import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.prediction_job import JobStatus


class JobCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    filename: str
    message: str = "Job queued for processing"


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    filename: str
    row_count: int | None
    processed_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobStatusResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
