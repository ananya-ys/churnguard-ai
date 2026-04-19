"""app/api/v1/endpoints/explain.py — SHAP explainability endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

from app.dependencies.auth import get_current_active_user
from app.dependencies.db import DBSession
from app.models.user import User
from app.schemas.predict import CustomerRecord
from app.services.explain_service import ExplainService
from pydantic import BaseModel, Field

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/explain", tags=["explainability"])


class ExplainRequest(BaseModel):
    records: list[CustomerRecord] = Field(
        min_length=1,
        max_length=50,
        description="Up to 50 customer records to explain",
    )
    top_n: int = Field(default=10, ge=1, le=30, description="Top N features to return per record")


@router.post("")
@limiter.limit("30/minute")
async def explain_predictions(
    request: Request,
    payload: ExplainRequest,
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    SHAP-based explanation for customer records.

    Returns:
    - Per-record: top features that pushed the prediction up/down
    - Global: mean absolute SHAP across all records in this batch
    - Expected value: baseline prediction without any features

    Note: SHAP is computationally heavier than /predict — rate limited to 30/min.
    Use /predict for high-throughput scoring; use /explain for interpretability.
    """
    svc = ExplainService(db)
    return await svc.explain_records(payload.records, top_n=payload.top_n)
