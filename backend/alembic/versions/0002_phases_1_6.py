"""
Alembic migration: 0002 — Phase 1-6 tables.

Adds:
  - experiment_runs (Phase 2: ML lifecycle tracking)
  - drift_reports (Phase 4: data drift)
  - ab_tests (Phase 6: A/B testing)

Also adds dataset_hash + estimator_key columns to model_versions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── experiment_runs ───────────────────────────────────────────────────────
    op.create_table(
        "experiment_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(16), unique=True, nullable=False),
        sa.Column("version_tag", sa.String(64), nullable=False),
        sa.Column("estimator_key", sa.String(32), nullable=False),
        sa.Column("dataset_path", sa.String(512), nullable=False),
        sa.Column("dataset_hash", sa.String(64), nullable=False),
        sa.Column("dataset_row_count", sa.Integer, nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("git_branch", sa.String(128), nullable=False, server_default="unknown"),
        sa.Column("triggered_by", sa.String(128), nullable=False, server_default="system"),
        sa.Column("hyperparameters", JSONB, nullable=True),
        sa.Column("feature_names", JSONB, nullable=True),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("feature_importance", JSONB, nullable=True),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0"),
        sa.Column("auc_gate_passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("promoted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_experiment_runs_run_id", "experiment_runs", ["run_id"])
    op.create_index("ix_experiment_runs_version_tag", "experiment_runs", ["version_tag"])
    op.create_index("ix_experiment_runs_created_at", "experiment_runs", ["created_at"])

    # ── drift_reports ─────────────────────────────────────────────────────────
    op.create_table(
        "drift_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_version_tag", sa.String(64), nullable=False),
        sa.Column("overall_drift_score", sa.Float, nullable=False),
        sa.Column("drift_detected", sa.Boolean, nullable=False),
        sa.Column("drifted_feature_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="none"),
        sa.Column("sample_size_train", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sample_size_live", sa.Integer, nullable=False, server_default="0"),
        sa.Column("feature_results", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_drift_reports_model_version_tag", "drift_reports", ["model_version_tag"])
    op.create_index("ix_drift_reports_created_at", "drift_reports", ["created_at"])

    # ── ab_tests ──────────────────────────────────────────────────────────────
    op.create_table(
        "ab_tests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("control_version_tag", sa.String(64), nullable=False),
        sa.Column("treatment_version_tag", sa.String(64), nullable=False),
        sa.Column("treatment_traffic_fraction", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("control_requests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("treatment_requests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("control_churn_sum", sa.Float, nullable=False, server_default="0"),
        sa.Column("treatment_churn_sum", sa.Float, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ab_tests_name", "ab_tests", ["name"])
    op.create_index("ix_ab_tests_is_active", "ab_tests", ["is_active"])

    # ── Add dataset_hash + estimator_key to model_versions ────────────────────
    op.add_column(
        "model_versions",
        sa.Column("dataset_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "model_versions",
        sa.Column("estimator_key", sa.String(32), nullable=True),
    )
    op.add_column(
        "model_versions",
        sa.Column("training_feature_stats", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_versions", "training_feature_stats")
    op.drop_column("model_versions", "estimator_key")
    op.drop_column("model_versions", "dataset_hash")
    op.drop_table("ab_tests")
    op.drop_table("drift_reports")
    op.drop_table("experiment_runs")
