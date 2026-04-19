"""app/models/model_version.py — Model version ORM model (updated for Phases 1-6)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        Index(
            "uix_model_versions_active",
            "is_active",
            unique=True,
            postgresql_where="is_active = TRUE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)

    auc_roc: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    f1_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    precision: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    recall: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    trained_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    training_data_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Phase 2: data lineage
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimator_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    training_feature_stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trained_by: Mapped["User | None"] = relationship(back_populates="model_versions", lazy="noload")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ModelVersion tag={self.version_tag} active={self.is_active} auc={self.auc_roc}>"
