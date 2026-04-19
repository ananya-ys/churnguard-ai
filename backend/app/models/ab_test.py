"""
app/models/ab_test.py — A/B test ORM model.

Phase 6 differentiator: route predictions across two model versions
and track per-variant churn rates for statistical comparison.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ABTest(Base):
    """
    Active A/B test definition.
    Maps to two model version tags and tracks traffic split.
    """

    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Control = current champion, treatment = challenger
    control_version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    treatment_version_tag: Mapped[str] = mapped_column(String(64), nullable=False)

    # Traffic split: 0.0–1.0 fraction routed to treatment
    treatment_traffic_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Live stats (updated per prediction)
    control_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    treatment_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    control_churn_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    treatment_churn_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ABTest name={self.name} control={self.control_version_tag} "
            f"treatment={self.treatment_version_tag} active={self.is_active}>"
        )
