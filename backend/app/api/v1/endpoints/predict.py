from typing import Annotated

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies.auth import get_current_active_user, require_role
from app.dependencies.db import DBSession
from app.models.user import User, UserRole
from app.schemas.predict import PredictRequest, PredictResponse
from app.services.predict_service import PredictService

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
@limiter.limit("100/minute")
async def predict(
    request: Request,
    payload: PredictRequest,
    db: DBSession,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> PredictResponse:
    """
    Real-time churn prediction for 1–500 customer records.
    SLO: p95 <= 200ms on 2 vCPU.
    Rate limit: 100 req/min (API_USER), 1000 req/min (ANALYST+).
    """
    service = PredictService(db)
    return await service.run_prediction(
        records=payload.records,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
