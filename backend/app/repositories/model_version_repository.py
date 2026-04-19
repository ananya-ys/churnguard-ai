"""app/repositories/model_version_repository.py — Updated to store lineage fields."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_version import ModelVersion


class ModelVersionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_active(self) -> ModelVersion | None:
        result = await self._db.execute(
            select(ModelVersion).where(ModelVersion.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, version_id: uuid.UUID) -> ModelVersion | None:
        result = await self._db.execute(
            select(ModelVersion).where(ModelVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tag(self, version_tag: str) -> ModelVersion | None:
        result = await self._db.execute(
            select(ModelVersion).where(ModelVersion.version_tag == version_tag)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModelVersion]:
        result = await self._db.execute(
            select(ModelVersion).order_by(ModelVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        version_tag: str,
        artifact_path: str,
        auc_roc: float,
        f1_score: float,
        precision: float,
        recall: float,
        trained_by_id: uuid.UUID | None = None,
        training_data_path: str | None = None,
        row_count: int | None = None,
        # Phase 2: lineage fields
        dataset_hash: str | None = None,
        estimator_key: str | None = None,
        training_feature_stats: dict | None = None,
    ) -> ModelVersion:
        mv = ModelVersion(
            version_tag=version_tag,
            artifact_path=artifact_path,
            auc_roc=auc_roc,
            f1_score=f1_score,
            precision=precision,
            recall=recall,
            trained_by_id=trained_by_id,
            training_data_path=training_data_path,
            row_count=row_count,
            is_active=False,
            dataset_hash=dataset_hash,
            estimator_key=estimator_key,
            training_feature_stats=training_feature_stats,
        )
        self._db.add(mv)
        await self._db.flush()
        await self._db.refresh(mv)
        return mv

    async def promote(self, version_id: uuid.UUID) -> ModelVersion | None:
        current = await self.get_active()
        if current:
            current.is_active = False
        target = await self.get_by_id(version_id)
        if target:
            target.is_active = True
            target.promoted_at = datetime.now(UTC)
        return target

    async def get_previous_active(self, exclude_id: uuid.UUID) -> ModelVersion | None:
        result = await self._db.execute(
            select(ModelVersion)
            .where(ModelVersion.id != exclude_id, ModelVersion.is_active.is_(False))
            .order_by(ModelVersion.promoted_at.desc().nullslast())
            .limit(1)
        )
        return result.scalar_one_or_none()
