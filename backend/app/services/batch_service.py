import uuid
from pathlib import Path

import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import FileTooLargeException, InvalidFileException, NotFoundException
from app.models.audit_log import AuditAction
from app.models.prediction_job import PredictionJob
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prediction_job_repository import PredictionJobRepository
from app.schemas.batch import JobCreateResponse, JobListResponse, JobStatusResponse

logger = structlog.get_logger(__name__)

ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/octet-stream"}
ALLOWED_EXTENSIONS = {".csv"}


class BatchService:
    def __init__(self, db: AsyncSession) -> None:
        self._job_repo = PredictionJobRepository(db)
        self._audit_repo = AuditLogRepository(db)
        self._db = db

    async def upload_csv(
        self,
        file: UploadFile,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> JobCreateResponse:
        # Validate extension
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidFileException(f"File must be a CSV. Got: {suffix}")

        # Validate MIME type (content type can be octet-stream in some clients)
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise InvalidFileException(
                f"Invalid MIME type: {file.content_type}. Expected text/csv"
            )

        # Read and validate size
        content = await file.read()
        if len(content) > settings.max_upload_size_bytes:
            raise FileTooLargeException(
                f"File exceeds {settings.max_upload_size_mb}MB limit"
            )

        # Save to disk
        job_id = uuid.uuid4()
        save_dir = Path(settings.upload_dir) / str(user_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{job_id}.csv"
        file_path.write_bytes(content)

        # Create job record
        job = await self._job_repo.create(
            user_id=user_id,
            filename=file.filename or "upload.csv",
            file_path=str(file_path),
        )

        await self._audit_repo.create(
            action=AuditAction.BATCH_UPLOAD,
            actor_id=user_id,
            entity_type="prediction_job",
            entity_id=str(job.id),
            ip_address=ip_address,
        )
        await self._db.commit()

        # Enqueue Celery task — import here to avoid circular deps
        from app.tasks.batch_predict import process_batch_job
        process_batch_job.delay(str(job.id))

        logger.info(
            "batch_job_queued",
            job_id=str(job.id),
            user_id=str(user_id),
            filename=file.filename,
            size_bytes=len(content),
        )

        return JobCreateResponse(
            job_id=job.id,
            status=job.status,
            filename=job.filename,
        )

    async def get_job_status(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> JobStatusResponse:
        if is_admin:
            job = await self._job_repo.get_by_id(job_id)
        else:
            job = await self._job_repo.get_by_id_and_user(job_id, user_id)

        if job is None:
            raise NotFoundException(f"Job {job_id} not found")

        return JobStatusResponse.model_validate(job)

    async def list_user_jobs(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> JobListResponse:
        jobs, total = await self._job_repo.list_by_user(user_id, page, page_size)
        return JobListResponse(
            items=[JobStatusResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
        )
