"""
app/services/drift_service.py — Data drift detection service.

Phase 4: Compares training distribution against recent live prediction inputs.
Pulls live feature values from audit_logs.prediction_result JSONB.
"""

import json
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.drift import (
    TRACKED_NUMERIC_FEATURES,
    compute_drift_report,
)
from app.core.metrics import (
    DRIFT_ALERTS_COUNTER,
    DRIFT_KS_PVALUE_GAUGE,
    DRIFT_PSI_GAUGE,
    OVERALL_DRIFT_SCORE_GAUGE,
)
from app.models.audit_log import AuditAction, AuditLog
from app.models.model_version import ModelVersion
from app.repositories.drift_repository import DriftRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.schemas.drift import DriftReportResponse, TriggerDriftCheckResponse

logger = structlog.get_logger(__name__)


class DriftService:
    def __init__(self, db: AsyncSession) -> None:
        self._drift_repo = DriftRepository(db)
        self._model_repo = ModelVersionRepository(db)
        self._db = db

    async def _get_live_feature_stats(
        self,
        hours: int = 24,
    ) -> dict[str, list[float]]:
        """
        Extract numeric feature values from recent prediction audit logs.
        Audit logs store prediction_result JSONB — we query the raw input
        feature stats that were stored during batch or real-time prediction.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        # Pull prediction audit logs with stored feature data
        result = await self._db.execute(
            select(AuditLog.prediction_result)
            .where(
                AuditLog.action == AuditAction.PREDICT,
                AuditLog.created_at >= cutoff,
                AuditLog.prediction_result.is_not(None),
            )
            .limit(2000)
        )
        rows = result.scalars().all()

        live_stats: dict[str, list[float]] = {f: [] for f in TRACKED_NUMERIC_FEATURES}

        for row in rows:
            if not isinstance(row, dict):
                continue
            features = row.get("input_features", {})
            for feat in TRACKED_NUMERIC_FEATURES:
                if feat in features and features[feat] is not None:
                    try:
                        live_stats[feat].append(float(features[feat]))
                    except (TypeError, ValueError):
                        pass

        return {k: v for k, v in live_stats.items() if len(v) >= 10}

    async def _get_training_feature_stats(
        self,
        version_tag: str,
    ) -> dict[str, list[float]]:
        """
        Load training feature statistics stored during model registration.
        Falls back to generating from training data if not available.
        """
        # Try to get from model version metadata (stored during train.py)
        result = await self._db.execute(
            select(ModelVersion).where(ModelVersion.version_tag == version_tag)
        )
        mv = result.scalar_one_or_none()

        if mv is None:
            return {}

        # Training data path may be available
        train_path = mv.training_data_path
        if not train_path:
            return {}

        try:
            import pandas as pd
            from pathlib import Path

            if not Path(train_path).exists():
                return {}

            df = pd.read_csv(train_path)
            stats: dict[str, list[float]] = {}
            for feat in TRACKED_NUMERIC_FEATURES:
                if feat in df.columns:
                    values = df[feat].dropna().tolist()
                    stats[feat] = [float(v) for v in values]
            return stats
        except Exception as e:
            logger.warning("training_stats_load_failed", error=str(e))
            return {}

    async def run_drift_check(
        self,
        model_version_tag: str | None = None,
        lookback_hours: int = 24,
    ) -> TriggerDriftCheckResponse:
        """
        Full drift check: load training distribution, compare vs live, save report.
        """
        if model_version_tag is None:
            active = await self._model_repo.get_active()
            if active is None:
                from app.core.exceptions import NotFoundException
                raise NotFoundException("No active model to check drift against")
            model_version_tag = active.version_tag

        logger.info("drift_check_started", version_tag=model_version_tag, hours=lookback_hours)

        # Collect distributions
        train_stats = await self._get_training_feature_stats(model_version_tag)
        live_stats = await self._get_live_feature_stats(hours=lookback_hours)

        if not train_stats:
            logger.warning("no_training_stats", version_tag=model_version_tag)
            train_stats = {}

        if not live_stats:
            logger.warning("no_live_stats", hours=lookback_hours)

        # Compute drift report
        report = compute_drift_report(
            train_feature_stats=train_stats,
            live_feature_stats=live_stats,
            computed_at=datetime.now(UTC).isoformat(),
        )

        # Update Prometheus gauges
        OVERALL_DRIFT_SCORE_GAUGE.set(report.overall_drift_score)
        for fr in report.feature_results:
            if fr.psi is not None:
                DRIFT_PSI_GAUGE.labels(feature=fr.feature).set(fr.psi)
            if fr.ks_pvalue is not None:
                DRIFT_KS_PVALUE_GAUGE.labels(feature=fr.feature).set(fr.ks_pvalue)
            if fr.drift_detected:
                DRIFT_ALERTS_COUNTER.labels(
                    feature=fr.feature, severity=fr.severity
                ).inc()

        # Persist report
        feature_results_serialized = [
            {
                "feature": fr.feature,
                "psi": fr.psi,
                "ks_statistic": fr.ks_statistic,
                "ks_pvalue": fr.ks_pvalue,
                "drift_detected": fr.drift_detected,
                "severity": fr.severity,
                "train_mean": fr.train_mean,
                "live_mean": fr.live_mean,
                "train_std": fr.train_std,
                "live_std": fr.live_std,
            }
            for fr in report.feature_results
        ]

        db_report = await self._drift_repo.create(
            model_version_tag=model_version_tag,
            overall_drift_score=report.overall_drift_score,
            drift_detected=report.drift_detected,
            drifted_feature_count=report.drifted_feature_count,
            severity=report.severity,
            sample_size_train=report.sample_size_train,
            sample_size_live=report.sample_size_live,
            feature_results=feature_results_serialized,
        )
        await self._db.commit()

        if report.drift_detected:
            logger.warning(
                "drift_detected",
                version_tag=model_version_tag,
                severity=report.severity,
                score=report.overall_drift_score,
                n_drifted=report.drifted_feature_count,
            )
        else:
            logger.info("drift_check_clean", version_tag=model_version_tag)

        return TriggerDriftCheckResponse(
            message=(
                f"Drift {'detected' if report.drift_detected else 'not detected'} "
                f"(severity={report.severity})"
            ),
            report_id=db_report.id,
            drift_detected=report.drift_detected,
            severity=report.severity,
            overall_drift_score=report.overall_drift_score,
            drifted_feature_count=report.drifted_feature_count,
        )

    async def get_latest_report(
        self, model_version_tag: str | None = None
    ) -> DriftReportResponse | None:
        report = await self._drift_repo.get_latest(model_version_tag)
        if report is None:
            return None
        return DriftReportResponse.model_validate(report)

    async def list_reports(
        self, page: int = 1, page_size: int = 20
    ) -> list[DriftReportResponse]:
        reports = await self._drift_repo.list_all(page=page, page_size=page_size)
        return [DriftReportResponse.model_validate(r) for r in reports]
