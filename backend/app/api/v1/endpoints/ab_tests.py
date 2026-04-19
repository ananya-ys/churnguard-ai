"""app/api/v1/endpoints/ab_tests.py — A/B testing between model versions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_active_user, require_role
from app.dependencies.db import DBSession
from app.models.user import User, UserRole
from app.schemas.drift import ABTestCreate, ABTestResponse, ABTestStopResponse
from app.services.ab_test_service import ABTestService

router = APIRouter(prefix="/ab-tests", tags=["ab-testing"])

_ml_or_admin = require_role(UserRole.ADMIN, UserRole.ML_ENGINEER)


@router.post("", response_model=ABTestResponse, status_code=201)
async def create_ab_test(
    payload: ABTestCreate,
    db: DBSession,
    _: Annotated[User, Depends(_ml_or_admin)],
) -> ABTestResponse:
    """
    Start an A/B test between two model versions.

    Traffic is split based on treatment_traffic_fraction.
    Example: 0.2 → 20% to treatment, 80% to control.

    Only one A/B test can be active at a time.
    Stop the current one before starting a new one.
    """
    svc = ABTestService(db)
    return await svc.create_test(payload)


@router.get("/active", response_model=ABTestResponse | None)
async def get_active_test(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> ABTestResponse | None:
    """Get the currently running A/B test, or null if none active."""
    svc = ABTestService(db)
    return await svc.get_active_test()


@router.get("", response_model=list[ABTestResponse])
async def list_ab_tests(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> list[ABTestResponse]:
    """List all A/B tests (active and historical)."""
    svc = ABTestService(db)
    return await svc.list_tests()


@router.post("/{test_id}/stop", response_model=ABTestStopResponse)
async def stop_ab_test(
    test_id: uuid.UUID,
    db: DBSession,
    _: Annotated[User, Depends(_ml_or_admin)],
) -> ABTestStopResponse:
    """
    Stop an A/B test and declare a winner.
    Lower mean churn probability = better model.
    """
    svc = ABTestService(db)
    return await svc.stop_test(test_id)
