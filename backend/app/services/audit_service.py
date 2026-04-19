import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.repositories.audit_log_repository import AuditLogRepository

logger = structlog.get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AuditLogRepository(db)
        self._db = db

    async def log_prediction(
        self,
        actor_id: uuid.UUID,
        input_hash: str,
        prediction_result: dict,
        model_version_tag: str,
        latency_ms: int,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = await self._repo.create(
            action=AuditAction.PREDICT,
            actor_id=actor_id,
            entity_type="prediction",
            input_hash=input_hash,
            prediction_result=prediction_result,
            model_version_tag=model_version_tag,
            ip_address=ip_address,
            latency_ms=latency_ms,
        )
        return log

    async def log_action(
        self,
        action: AuditAction,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        model_version_tag: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = await self._repo.create(
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            model_version_tag=model_version_tag,
            ip_address=ip_address,
        )
        return log

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        action: AuditAction | None = None,
    ) -> list[AuditLog]:
        return await self._repo.list_all(page=page, page_size=page_size, action=action)
