from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import require_role
from app.dependencies.db import DBSession
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])

_admin_only = require_role(UserRole.ADMIN)


class AuditLogResponse:
    pass


from pydantic import BaseModel


class AuditLogItem(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: AuditAction
    entity_type: str | None
    entity_id: str | None
    input_hash: str | None
    model_version_tag: str | None
    ip_address: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogItem])
async def list_audit_logs(
    db: DBSession,
    _: Annotated[User, Depends(_admin_only)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: AuditAction | None = Query(None),
) -> list[AuditLogItem]:
    """Admin-only. Returns append-only audit trail with optional action filter."""
    service = AuditService(db)
    logs = await service.list_logs(page=page, page_size=page_size, action=action)
    return [AuditLogItem.model_validate(log) for log in logs]
