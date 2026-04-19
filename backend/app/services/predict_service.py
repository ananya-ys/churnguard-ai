"""
app/services/predict_service.py — Prediction service with Prometheus metrics + A/B testing.

Phase 3: Records prediction latency, churn rate, confidence bands to Prometheus.
Phase 6: Routes traffic through A/B test if one is active, using per-variant models.
"""

import hashlib
import json
import time
import uuid
from typing import Any, Literal

import joblib
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    CHURN_PROBABILITY_HISTOGRAM,
    CHURN_RATE_GAUGE,
    PREDICTION_COUNTER,
    PREDICTION_LATENCY,
)
from app.ml.pipeline import FEATURE_COLUMNS, pipeline_manager
from app.models.audit_log import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.predict import CustomerRecord, PredictionResult, PredictResponse

logger = structlog.get_logger(__name__)

CHURN_THRESHOLD = 0.5


def _confidence_band(prob: float) -> Literal["low", "mid", "high"]:
    if prob < 0.3:
        return "low"
    if prob < 0.7:
        return "mid"
    return "high"


def _compute_hash(record_dict: dict) -> str:
    serialised = json.dumps(record_dict, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _predict_with_artifact(artifact_path: str, record_dicts: list[dict]) -> list[float]:
    """Load and run a specific model artifact (for A/B testing non-active variant)."""
    import pandas as pd
    import numpy as np

    pipeline = joblib.load(artifact_path)
    df = pd.DataFrame(record_dicts, columns=FEATURE_COLUMNS)
    probas: Any = pipeline.predict_proba(df)
    return probas[:, 1].tolist()


class PredictService:
    def __init__(self, db: AsyncSession) -> None:
        self._audit_repo = AuditLogRepository(db)
        self._db = db

    async def run_prediction(
        self,
        records: list[CustomerRecord],
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> PredictResponse:
        start = time.monotonic()

        record_dicts = [r.model_dump() for r in records]

        # ── Phase 6: A/B test routing ─────────────────────────────────────────
        ab_variant: str | None = None
        ab_test_id: uuid.UUID | None = None

        try:
            from app.services.ab_test_service import ABTestService
            ab_svc = ABTestService(self._db)
            ab_variant, ab_artifact_path, ab_test_id = (
                await ab_svc.select_variant_for_prediction()
            )
        except Exception:
            ab_variant = None
            ab_artifact_path = None
            ab_test_id = None

        # Run predictions
        if ab_variant is not None and ab_artifact_path is not None:
            # Use the variant's specific artifact (may differ from active model)
            probabilities = _predict_with_artifact(ab_artifact_path, record_dicts)
            model_version = (
                f"{ab_variant}:{ab_artifact_path.split('/')[-1].replace('.pkl', '')}"
            )
        else:
            # Normal path: use active loaded pipeline
            probabilities = pipeline_manager.predict(record_dicts)
            model_version = pipeline_manager.get_version()

        # ── Build results ────────────────────────────────────────────────────
        results: list[PredictionResult] = []
        for record_dict, prob in zip(record_dicts, probabilities):
            input_hash = _compute_hash(record_dict)
            result = PredictionResult(
                churn=prob >= CHURN_THRESHOLD,
                churn_probability=round(prob, 6),
                confidence_band=_confidence_band(prob),
                input_hash=input_hash,
            )
            results.append(result)

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        clean_version = model_version.split(":")[-1] if ":" in model_version else model_version

        # ── Phase 3: Prometheus metrics ───────────────────────────────────────
        # Record prediction latency using the wall-clock time captured above
        PREDICTION_LATENCY.labels(model_version=clean_version).observe(
            (time.monotonic() - start)
        )

        churn_count = sum(1 for r in results if r.churn)
        for result in results:
            PREDICTION_COUNTER.labels(
                model_version=clean_version,
                confidence_band=result.confidence_band,
            ).inc()
            CHURN_PROBABILITY_HISTOGRAM.labels(model_version=clean_version).observe(
                result.churn_probability
            )

        churn_rate = churn_count / len(results) if results else 0.0
        CHURN_RATE_GAUGE.labels(model_version=clean_version).set(churn_rate)

        # ── Phase 6: Record A/B test result ──────────────────────────────────
        if ab_variant and ab_test_id:
            try:
                mean_prob = sum(r.churn_probability for r in results) / len(results)
                ab_svc = ABTestService(self._db)
                await ab_svc.record_ab_prediction(ab_test_id, ab_variant, mean_prob)
            except Exception as e:
                logger.warning("ab_test_record_failed", error=str(e))

        # ── Audit log ─────────────────────────────────────────────────────────
        summary = {
            "record_count": len(results),
            "churn_count": churn_count,
            "model_version": model_version,
            "ab_variant": ab_variant,
            "input_features": record_dicts[0] if len(record_dicts) == 1 else {},
        }

        await self._audit_repo.create(
            action=AuditAction.PREDICT,
            actor_id=user_id,
            entity_type="prediction_batch",
            input_hash=results[0].input_hash if results else None,
            prediction_result=summary,
            model_version_tag=clean_version,
            ip_address=ip_address,
            latency_ms=int(latency_ms),
        )
        await self._db.commit()

        logger.info(
            "prediction_complete",
            user_id=str(user_id),
            record_count=len(results),
            churn_count=churn_count,
            latency_ms=latency_ms,
            model_version=model_version,
            ab_variant=ab_variant,
        )

        return PredictResponse(
            predictions=results,
            model_version=model_version,
            record_count=len(results),
            latency_ms=latency_ms,
        )
