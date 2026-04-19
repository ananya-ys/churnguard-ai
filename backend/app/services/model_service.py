"""app/services/model_service.py — Model service (updated: Prometheus metrics, lineage)."""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_model_cache
from app.core.config import settings
from app.core.exceptions import AUCGateException, ConflictException, NotFoundException
from app.core.metrics import (
    ACTIVE_MODEL_INFO,
    MODEL_AUC_GAUGE,
    MODEL_F1_GAUGE,
    MODEL_PROMOTIONS_COUNTER,
    MODEL_ROLLBACKS_COUNTER,
)
from app.ml.pipeline import pipeline_manager
from app.models.audit_log import AuditAction
from app.models.model_version import ModelVersion
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.schemas.model_version import ModelVersionRegister

logger = structlog.get_logger(__name__)


class ModelService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ModelVersionRepository(db)
        self._audit_repo = AuditLogRepository(db)
        self._db = db

    async def register_version(
        self,
        payload: ModelVersionRegister,
        trained_by_id: uuid.UUID | None = None,
    ) -> ModelVersion:
        existing = await self._repo.get_by_tag(payload.version_tag)
        if existing:
            raise ConflictException(f"Version tag '{payload.version_tag}' already exists")

        mv = await self._repo.create(
            version_tag=payload.version_tag,
            artifact_path=payload.artifact_path,
            auc_roc=payload.auc_roc,
            f1_score=payload.f1_score,
            precision=payload.precision,
            recall=payload.recall,
            trained_by_id=trained_by_id,
            training_data_path=payload.training_data_path,
            row_count=payload.row_count,
            dataset_hash=payload.dataset_hash,
            estimator_key=payload.estimator_key,
            training_feature_stats=payload.training_feature_stats,
        )

        await self._audit_repo.create(
            action=AuditAction.MODEL_REGISTER,
            actor_id=trained_by_id,
            entity_type="model_version",
            entity_id=str(mv.id),
            model_version_tag=mv.version_tag,
        )
        await self._db.commit()

        # Phase 3: update Prometheus gauges
        MODEL_AUC_GAUGE.labels(version_tag=mv.version_tag).set(float(mv.auc_roc))
        MODEL_F1_GAUGE.labels(version_tag=mv.version_tag).set(float(mv.f1_score))

        logger.info(
            "model_registered",
            version_tag=mv.version_tag,
            auc=float(mv.auc_roc),
            dataset_hash=payload.dataset_hash,
            estimator_key=payload.estimator_key,
        )
        return mv

    async def promote_version(
        self,
        version_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> ModelVersion:
        mv = await self._repo.get_by_id(version_id)
        if mv is None:
            raise NotFoundException(f"Model version {version_id} not found")

        if float(mv.auc_roc) < settings.min_auc_threshold:
            raise AUCGateException(float(mv.auc_roc), settings.min_auc_threshold)

        promoted = await self._repo.promote(version_id)
        if promoted is None:
            raise NotFoundException("Promotion failed — version not found")

        await self._audit_repo.create(
            action=AuditAction.MODEL_PROMOTE,
            actor_id=actor_id,
            entity_type="model_version",
            entity_id=str(promoted.id),
            model_version_tag=promoted.version_tag,
        )
        await self._db.commit()

        pipeline_manager.swap(promoted.artifact_path, promoted.version_tag)
        await invalidate_model_cache()

        # Phase 3: Prometheus + invalidate SHAP cache
        MODEL_PROMOTIONS_COUNTER.labels(version_tag=promoted.version_tag).inc()
        ACTIVE_MODEL_INFO.info({"version_tag": promoted.version_tag, "status": "promoted"})

        from app.ml.explainer import invalidate_explainer_cache
        invalidate_explainer_cache()

        logger.info("model_promoted", version_tag=promoted.version_tag)
        return promoted

    async def rollback_version(
        self,
        actor_id: uuid.UUID | None = None,
    ) -> ModelVersion:
        current = await self._repo.get_active()
        if current is None:
            raise NotFoundException("No active model to roll back")

        previous = await self._repo.get_previous_active(exclude_id=current.id)
        if previous is None:
            raise NotFoundException("No previous model version available for rollback")

        current.is_active = False
        previous.is_active = True
        previous.promoted_at = datetime.now(UTC)

        await self._audit_repo.create(
            action=AuditAction.MODEL_ROLLBACK,
            actor_id=actor_id,
            entity_type="model_version",
            entity_id=str(previous.id),
            model_version_tag=previous.version_tag,
        )
        await self._db.commit()

        pipeline_manager.swap(previous.artifact_path, previous.version_tag)
        await invalidate_model_cache()

        MODEL_ROLLBACKS_COUNTER.inc()
        from app.ml.explainer import invalidate_explainer_cache
        invalidate_explainer_cache()

        logger.info(
            "model_rollback",
            from_version=current.version_tag,
            to_version=previous.version_tag,
        )
        return previous

    async def get_active(self) -> ModelVersion | None:
        return await self._repo.get_active()

    async def list_versions(self) -> list[ModelVersion]:
        return await self._repo.list_all()
