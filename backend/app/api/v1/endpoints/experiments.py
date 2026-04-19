"""app/api/v1/endpoints/experiments.py — ML experiment tracking API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_active_user, require_role
from app.dependencies.db import DBSession
from app.models.user import User, UserRole
from app.schemas.experiment import (
    ExperimentCompareResponse,
    ExperimentRunResponse,
)
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["ml-lifecycle"])

_ml_or_admin = require_role(UserRole.ADMIN, UserRole.ML_ENGINEER)


@router.get("", response_model=list[ExperimentRunResponse])
async def list_experiments(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[ExperimentRunResponse]:
    """
    List all training experiment runs — newest first.
    Shows dataset hash, git commit, all metrics, feature importance.
    """
    svc = ExperimentService(db)
    return await svc.list_runs(page=page, page_size=page_size)


@router.get("/{run_id}", response_model=ExperimentRunResponse)
async def get_experiment(
    run_id: str,
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> ExperimentRunResponse:
    """Get a single experiment run by its run_id."""
    svc = ExperimentService(db)
    return await svc.get_run(run_id)


@router.get("/compare/{run_id_a}/{run_id_b}", response_model=ExperimentCompareResponse)
async def compare_experiments(
    run_id_a: str,
    run_id_b: str,
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> ExperimentCompareResponse:
    """
    Side-by-side metric comparison of two experiment runs.
    Returns per-metric delta and overall winner.
    """
    svc = ExperimentService(db)
    return await svc.compare_runs(run_id_a, run_id_b)
