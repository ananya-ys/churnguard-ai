import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog


class AuditLogRepository:
    """Append-only. No update or delete methods exist on this repository."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        action: AuditAction,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        input_hash: str | None = None,
        prediction_result: dict | None = None,
        model_version_tag: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        latency_ms: int | None = None,
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            input_hash=input_hash,
            prediction_result=prediction_result,
            model_version_tag=model_version_tag,
            ip_address=ip_address,
            user_agent=user_agent,
            latency_ms=latency_ms,
        )
        self._db.add(log)
        await self._db.flush()
        return log

    async def list_by_actor(
        self,
        actor_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditLog]:
        result = await self._db.execute(
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
        action: AuditAction | None = None,
    ) -> list[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        if action:
            query = query.where(AuditLog.action == action)
        result = await self._db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all())
