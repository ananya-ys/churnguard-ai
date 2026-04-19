import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    REGISTER = "register"
    PREDICT = "predict"
    BATCH_UPLOAD = "batch_upload"
    BATCH_COMPLETE = "batch_complete"
    BATCH_FAIL = "batch_fail"
    MODEL_REGISTER = "model_register"
    MODEL_PROMOTE = "model_promote"
    MODEL_ROLLBACK = "model_rollback"
    RETRAIN_SUCCESS = "retrain_success"
    RETRAIN_FAIL = "retrain_fail"


class AuditLog(Base):
    """
    Append-only audit log. No UPDATE or DELETE operations permitted.
    Every prediction and action permanently recorded.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_input_hash", "input_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prediction_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_version_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    actor: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="audit_logs", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} actor={self.actor_id}>"
