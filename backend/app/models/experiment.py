"""
app/models/experiment.py — Experiment run ORM model.

Phase 2: Every training run produces one row here.
Captures full lineage: data, code, hyperparams, metrics.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExperimentRun(Base):
    """
    Immutable training run record.
    Written once — no updates. Append-only for audit lineage.
    """

    __tablename__ = "experiment_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    estimator_key: Mapped[str] = mapped_column(String(32), nullable=False)

    # Data lineage
    dataset_path: Mapped[str] = mapped_column(String(512), nullable=False)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_row_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Code lineage
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    git_branch: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")

    # Hyperparameters + features (JSONB for queryability)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feature_names: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Metrics
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feature_importance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Artifact
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Gate + promotion status
    auc_gate_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Optional notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ExperimentRun run_id={self.run_id} version={self.version_tag} "
            f"auc={self.metrics.get('auc_roc') if self.metrics else '?'} "
            f"promoted={self.promoted}>"
        )
