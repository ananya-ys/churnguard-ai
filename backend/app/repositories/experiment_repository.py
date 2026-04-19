"""app/repositories/experiment_repository.py — Experiment run repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import ExperimentRun


class ExperimentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> ExperimentRun:
        run = ExperimentRun(**kwargs)
        self._db.add(run)
        await self._db.flush()
        await self._db.refresh(run)
        return run

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[ExperimentRun]:
        result = await self._db.execute(
            select(ExperimentRun)
            .order_by(ExperimentRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def get_by_run_id(self, run_id: str) -> ExperimentRun | None:
        result = await self._db.execute(
            select(ExperimentRun).where(ExperimentRun.run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_by_version_tag(self, version_tag: str) -> ExperimentRun | None:
        result = await self._db.execute(
            select(ExperimentRun)
            .where(ExperimentRun.version_tag == version_tag)
            .order_by(ExperimentRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_promoted(self) -> list[ExperimentRun]:
        result = await self._db.execute(
            select(ExperimentRun)
            .where(ExperimentRun.promoted.is_(True))
            .order_by(ExperimentRun.created_at.desc())
        )
        return list(result.scalars().all())
