"""
app/services/ab_test_service.py — A/B testing between model versions.

Phase 6: Route a configurable fraction of prediction traffic to a challenger
model. Track per-variant churn rates for statistical comparison.

Architecture:
  - ABTest row defines control + treatment model version tags
  - On each /predict call, check if active A/B test exists (Redis cache)
  - Route to variant based on traffic fraction + random roll
  - Load correct model artifact for the selected variant
  - Record result to ab_tests row (atomic UPDATE)
"""

import random
import uuid
from datetime import UTC, datetime
from typing import Any

import joblib
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.exceptions import ConflictException, NotFoundException
from app.core.metrics import AB_TEST_CHURN_RATE_GAUGE, AB_TEST_REQUEST_COUNTER
from app.models.ab_test import ABTest
from app.repositories.ab_test_repository import ABTestRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.schemas.drift import (
    ABTestCreate,
    ABTestResponse,
    ABTestStats,
    ABTestStopResponse,
)

logger = structlog.get_logger(__name__)

_AB_TEST_CACHE_KEY = "ab_test:active"
_AB_TEST_TTL = 30  # seconds — short TTL so traffic split changes propagate quickly


class ABTestService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ABTestRepository(db)
        self._model_repo = ModelVersionRepository(db)
        self._db = db

    async def create_test(self, payload: ABTestCreate) -> ABTestResponse:
        """Create a new A/B test. Fails if another test is already active."""
        existing_active = await self._repo.get_active()
        if existing_active:
            raise ConflictException(
                f"A/B test '{existing_active.name}' is already active. "
                "Stop it before starting a new one."
            )

        existing_named = await self._repo.get_by_name(payload.name)
        if existing_named:
            raise ConflictException(f"A/B test with name '{payload.name}' already exists")

        # Validate both model versions exist
        for tag in (payload.control_version_tag, payload.treatment_version_tag):
            mv = await self._model_repo.get_by_tag(tag)
            if mv is None:
                raise NotFoundException(f"Model version '{tag}' not found")

        test = await self._repo.create(
            name=payload.name,
            control_version_tag=payload.control_version_tag,
            treatment_version_tag=payload.treatment_version_tag,
            treatment_traffic_fraction=payload.treatment_traffic_fraction,
            description=payload.description,
        )
        await self._db.commit()

        # Invalidate cache so next prediction picks up new test
        from app.core.cache import cache_delete
        await cache_delete(_AB_TEST_CACHE_KEY)

        logger.info(
            "ab_test_created",
            name=test.name,
            control=test.control_version_tag,
            treatment=test.treatment_version_tag,
            fraction=test.treatment_traffic_fraction,
        )

        return self._to_response(test)

    async def get_active_test(self) -> ABTestResponse | None:
        test = await self._repo.get_active()
        if test is None:
            return None
        return self._to_response(test)

    async def list_tests(self) -> list[ABTestResponse]:
        tests = await self._repo.list_all()
        return [self._to_response(t) for t in tests]

    async def stop_test(self, test_id: uuid.UUID) -> ABTestStopResponse:
        test = await self._repo.stop(test_id)
        if test is None:
            raise NotFoundException(f"A/B test {test_id} not found")
        await self._db.commit()

        from app.core.cache import cache_delete
        await cache_delete(_AB_TEST_CACHE_KEY)

        # Compute winner
        ctrl_mean = (
            test.control_churn_sum / test.control_requests
            if test.control_requests > 0 else None
        )
        trt_mean = (
            test.treatment_churn_sum / test.treatment_requests
            if test.treatment_requests > 0 else None
        )

        winner: str | None = None
        if ctrl_mean is not None and trt_mean is not None:
            # Lower churn probability = better model
            if trt_mean < ctrl_mean - 0.001:
                winner = f"treatment ({test.treatment_version_tag})"
            elif ctrl_mean < trt_mean - 0.001:
                winner = f"control ({test.control_version_tag})"
            else:
                winner = "inconclusive"

        logger.info(
            "ab_test_stopped",
            name=test.name,
            winner=winner,
            ctrl_mean=ctrl_mean,
            trt_mean=trt_mean,
        )

        return ABTestStopResponse(
            message=f"A/B test '{test.name}' stopped",
            test_id=test_id,
            winner=winner,
            control_mean_churn=ctrl_mean,
            treatment_mean_churn=trt_mean,
        )

    async def select_variant_for_prediction(
        self,
    ) -> tuple[str | None, str | None, uuid.UUID | None]:
        """
        Called at prediction time. Returns (variant, artifact_path, test_id) or
        (None, None, None) if no active A/B test.

        Caches the active test definition in Redis to avoid per-request DB hits.
        """
        # Try cache
        cached = await cache_get(_AB_TEST_CACHE_KEY)
        if cached == "__none__":
            return None, None, None

        test_data: dict | None = cached if isinstance(cached, dict) else None

        if test_data is None:
            # DB lookup
            test = await self._repo.get_active()
            if test is None:
                await cache_set(_AB_TEST_CACHE_KEY, "__none__", _AB_TEST_TTL)
                return None, None, None
            test_data = {
                "id": str(test.id),
                "name": test.name,
                "control_version_tag": test.control_version_tag,
                "treatment_version_tag": test.treatment_version_tag,
                "treatment_traffic_fraction": test.treatment_traffic_fraction,
            }
            await cache_set(_AB_TEST_CACHE_KEY, test_data, _AB_TEST_TTL)

        # Probabilistic routing
        roll = random.random()
        if roll < test_data["treatment_traffic_fraction"]:
            variant = "treatment"
            version_tag = test_data["treatment_version_tag"]
        else:
            variant = "control"
            version_tag = test_data["control_version_tag"]

        # Get artifact path for the selected version
        mv = await self._model_repo.get_by_tag(version_tag)
        if mv is None:
            logger.warning("ab_test_version_not_found", version_tag=version_tag)
            return None, None, None

        return variant, mv.artifact_path, uuid.UUID(test_data["id"])

    async def record_ab_prediction(
        self,
        test_id: uuid.UUID,
        variant: str,
        mean_churn_probability: float,
    ) -> None:
        """Record prediction result to A/B test counters."""
        await self._repo.record_prediction(test_id, variant, mean_churn_probability)
        await self._db.commit()

        AB_TEST_REQUEST_COUNTER.labels(
            experiment_name=str(test_id), variant=variant
        ).inc()
        AB_TEST_CHURN_RATE_GAUGE.labels(
            experiment_name=str(test_id), variant=variant
        ).set(mean_churn_probability)

    def _to_response(self, test: ABTest) -> ABTestResponse:
        ctrl_mean = (
            round(test.control_churn_sum / test.control_requests, 6)
            if test.control_requests > 0 else None
        )
        trt_mean = (
            round(test.treatment_churn_sum / test.treatment_requests, 6)
            if test.treatment_requests > 0 else None
        )

        return ABTestResponse(
            id=test.id,
            name=test.name,
            description=test.description,
            control_version_tag=test.control_version_tag,
            treatment_version_tag=test.treatment_version_tag,
            treatment_traffic_fraction=test.treatment_traffic_fraction,
            is_active=test.is_active,
            control_stats=ABTestStats(
                variant="control",
                requests=test.control_requests,
                mean_churn_probability=ctrl_mean,
                churn_rate_estimate=ctrl_mean,
            ),
            treatment_stats=ABTestStats(
                variant="treatment",
                requests=test.treatment_requests,
                mean_churn_probability=trt_mean,
                churn_rate_estimate=trt_mean,
            ),
            started_at=test.started_at,
            ended_at=test.ended_at,
            created_at=test.created_at,
        )
