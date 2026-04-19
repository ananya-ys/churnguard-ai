from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies.auth import get_current_active_user
from app.dependencies.db import DBSession
from app.models.user import User
from app.schemas.batch import JobCreateResponse
from app.services.batch_service import BatchService

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/upload", tags=["batch"])


@router.post("", response_model=JobCreateResponse, status_code=202)
@limiter.limit("10/hour")
async def upload_csv(
    request: Request,
    file: UploadFile,
    db: DBSession,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> JobCreateResponse:
    """
    Upload a CSV file for batch churn prediction.
    Max size: 50MB. Returns job_id immediately (<50ms). Poll /jobs/{id} for status.
    Rate limit: 10 uploads/hour per user.
    """
    service = BatchService(db)
    return await service.upload_csv(
        file=file,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
