import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.core.cache import TTL_JOB_STATUS, cache_get, cache_set, job_status_key
from app.core.exceptions import ForbiddenException, NotFoundException
from app.dependencies.auth import get_current_active_user
from app.dependencies.db import DBSession
from app.models.prediction_job import JobStatus
from app.models.user import User, UserRole
from app.schemas.batch import JobListResponse, JobStatusResponse
from app.services.batch_service import BatchService

router = APIRouter(prefix="/jobs", tags=["batch"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    db: DBSession,
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JobListResponse:
    service = BatchService(db)
    return await service.list_user_jobs(
        user_id=current_user.id, page=page, page_size=page_size
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    db: DBSession,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> JobStatusResponse:
    # Cache hit for polling (TTL 2s — prevents DB hammering)
    cached = await cache_get(job_status_key(str(job_id)))
    if cached:
        return JobStatusResponse(**cached)

    is_admin = current_user.role == UserRole.ADMIN
    service = BatchService(db)
    result = await service.get_job_status(
        job_id=job_id, user_id=current_user.id, is_admin=is_admin
    )

    # Only cache non-terminal states (terminal states don't change)
    if result.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
        await cache_set(job_status_key(str(job_id)), result.model_dump(mode="json"), TTL_JOB_STATUS)

    return result


@router.get("/{job_id}/results")
async def download_results(
    job_id: uuid.UUID,
    db: DBSession,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> FileResponse:
    is_admin = current_user.role == UserRole.ADMIN
    service = BatchService(db)
    job = await service.get_job_status(
        job_id=job_id, user_id=current_user.id, is_admin=is_admin
    )

    if job.status != JobStatus.COMPLETED:
        raise NotFoundException(f"Results not ready. Job status: {job.status}")

    if not job.result_path or not Path(job.result_path).exists():
        raise NotFoundException("Result file not found on disk")

    return FileResponse(
        path=job.result_path,
        media_type="text/csv",
        filename=f"churnguard_results_{job_id}.csv",
    )
