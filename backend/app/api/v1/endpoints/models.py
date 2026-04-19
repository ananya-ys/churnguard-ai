import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_active_user, require_role
from app.dependencies.db import DBSession
from app.models.user import User, UserRole
from app.schemas.model_version import (
    ModelPromoteResponse,
    ModelVersionRegister,
    ModelVersionResponse,
)
from app.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["models"])

_ml_engineer_or_admin = require_role(UserRole.ADMIN, UserRole.ML_ENGINEER)


# -----------------------------
# LIST MODELS (KEEP AUTH)
# -----------------------------
@router.get("", response_model=list[ModelVersionResponse])
async def list_model_versions(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> list[ModelVersionResponse]:
    service = ModelService(db)
    versions = await service.list_versions()
    return [ModelVersionResponse.model_validate(v) for v in versions]


# -----------------------------
# GET ACTIVE MODEL (KEEP AUTH)
# -----------------------------
@router.get("/active", response_model=ModelVersionResponse)
async def get_active_model(
    db: DBSession,
    _: Annotated[User, Depends(get_current_active_user)],
) -> ModelVersionResponse:
    from app.core.exceptions import NotFoundException

    service = ModelService(db)
    active = await service.get_active()
    if active is None:
        raise NotFoundException("No active model version found")
    return ModelVersionResponse.model_validate(active)


# -----------------------------
# 🚨 REGISTER MODEL (NO AUTH)
# -----------------------------
@router.post("", response_model=ModelVersionResponse, status_code=201)
async def register_model_version(
    payload: ModelVersionRegister,
    db: DBSession,
) -> ModelVersionResponse:
    service = ModelService(db)

    # 👇 SYSTEM USER (internal ML pipeline)
    mv = await service.register_version(
        payload,
        trained_by_id=None,  # no user → system registration
    )

    return ModelVersionResponse.model_validate(mv)


# -----------------------------
# PROMOTE MODEL (KEEP AUTH)
# -----------------------------
@router.post("/{version_id}/promote", response_model=ModelPromoteResponse)
async def promote_model(
    version_id: uuid.UUID,
    db: DBSession,
    current_user: Annotated[User, Depends(_ml_engineer_or_admin)],
) -> ModelPromoteResponse:
    service = ModelService(db)
    promoted = await service.promote_version(version_id, actor_id=current_user.id)
    return ModelPromoteResponse(
        message=f"Model '{promoted.version_tag}' promoted to active",
        version_tag=promoted.version_tag,
        promoted_at=promoted.promoted_at or datetime.now(UTC),
    )


# -----------------------------
# ROLLBACK MODEL (KEEP AUTH)
# -----------------------------
@router.post("/rollback", response_model=ModelPromoteResponse)
async def rollback_model(
    db: DBSession,
    current_user: Annotated[User, Depends(_ml_engineer_or_admin)],
) -> ModelPromoteResponse:
    service = ModelService(db)
    previous = await service.rollback_version(actor_id=current_user.id)
    return ModelPromoteResponse(
        message=f"Rolled back to model '{previous.version_tag}'",
        version_tag=previous.version_tag,
        promoted_at=previous.promoted_at or datetime.now(UTC),
    )