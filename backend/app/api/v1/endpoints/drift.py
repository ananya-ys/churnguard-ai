"""app/api/v1/endpoints/drift.py — Data drift monitoring API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_active_user, require_role
from app.dependencies.db import DBSession
from app.models.user import User, UserRole
from app.schemas.drift import DriftReportResponse, TriggerDriftCheckResponse
from app.services.drift_service import DriftService

router = APIRouter(prefix="/drift", tags=["drift-monitoring"])

_ml_or_admin = require_role(UserRole.ADMIN, UserRole.ML_ENGINEER)


@router.post("/check", response_model=TriggerDriftCheckResponse)
async def trigger_drift_check(
    db: DBSession,
    _: Annotated[User, Depends(_ml_or_admin)],
    lookback_hours: int = Query(24, ge=1, le=168, description="Hours of live data to compare"),
    model_version_tag: str | None = Query(None, description="Specific version (default: active)"),
) -> TriggerDriftCheckResponse:
    """
    Trigger an on-demand drift check.
    Compares training feature distribution vs recent prediction inputs.
    Uses PSI (Population Stability Index) + KS test.
    """
    svc = DriftService(db)
    return await svc.run_drift_check(
        model_version_tag=model_version_tag,
        lookback_hours=lookback_hours,
    )


@router.get("/latest", response_model=DriftReportResponse | None)
async def get_latest_drift_report(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
    model_version_tag: str | None = Query(None),
) -> DriftReportResponse | None:
    """Latest drift report (or None if no checks have run yet)."""
    svc = DriftService(db)
    return await svc.get_latest_report(model_version_tag)


@router.get("", response_model=list[DriftReportResponse])
async def list_drift_reports(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[DriftReportResponse]:
    """List all drift check runs — newest first."""
    svc = DriftService(db)
    return await svc.list_reports(page=page, page_size=page_size)
