import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction_job import JobStatus, PredictionJob


class PredictionJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_path: str,
    ) -> PredictionJob:
        job = PredictionJob(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            status=JobStatus.QUEUED,
        )
        self._db.add(job)
        await self._db.flush()
        await self._db.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> PredictionJob | None:
        result = await self._db.execute(
            select(PredictionJob).where(PredictionJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> PredictionJob | None:
        result = await self._db.execute(
            select(PredictionJob).where(
                PredictionJob.id == job_id,
                PredictionJob.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[PredictionJob], int]:
        base_query = select(PredictionJob).where(PredictionJob.user_id == user_id)
        total_result = await self._db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar_one()
        items_result = await self._db.execute(
            base_query.order_by(PredictionJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars().all()), total

    async def set_processing(self, job_id: uuid.UUID) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)

    async def set_completed(
        self, job_id: uuid.UUID, result_path: str, processed_count: int
    ) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.result_path = result_path
            job.processed_count = processed_count
            job.completed_at = datetime.now(UTC)

    async def set_failed(self, job_id: uuid.UUID, error_message: str) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error_message
            job.completed_at = datetime.now(UTC)

    async def increment_processed(self, job_id: uuid.UUID, count: int) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.processed_count += count
