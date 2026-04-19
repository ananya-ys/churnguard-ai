"""
app/models/drift_report.py — Drift report ORM model.

Phase 4: Each drift check run creates one row.
Tracks feature-level PSI/KS results and overall drift severity.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DriftReport(Base):
    """
    One drift check run — comparing training distribution vs recent live predictions.
    Append-only. Never updated after creation.
    """

    __tablename__ = "drift_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Which model version was checked
    model_version_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Summary
    overall_drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    drifted_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="none")

    # Sample sizes
    sample_size_train: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sample_size_live: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Per-feature results (JSONB list)
    feature_results: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<DriftReport id={self.id} model={self.model_version_tag} "
            f"drift={self.drift_detected} severity={self.severity}>"
        )
