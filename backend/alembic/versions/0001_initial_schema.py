"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-01 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── ENUMS (CREATE ONCE) ───────────────────────────────────────────────
    user_role_enum = postgresql.ENUM(
        "admin", "ml_engineer", "analyst", "api_user",
        name="user_role"
    )
    job_status_enum = postgresql.ENUM(
        "queued", "processing", "completed", "failed",
        name="job_status"
    )
    audit_action_enum = postgresql.ENUM(
        "login", "register", "predict",
        "batch_upload", "batch_complete", "batch_fail",
        "model_register", "model_promote", "model_rollback",
        "retrain_success", "retrain_fail",
        name="audit_action"
    )

    # Create safely (idempotent)
    user_role_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)
    audit_action_enum.create(bind, checkfirst=True)

    # ── REUSE ENUMS (NO RE-CREATION) ──────────────────────────────────────
    user_role = postgresql.ENUM(name="user_role", create_type=False)
    job_status = postgresql.ENUM(name="job_status", create_type=False)
    audit_action = postgresql.ENUM(name="audit_action", create_type=False)

    # ── USERS ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── MODEL VERSIONS ───────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_tag", sa.String(64), nullable=False),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("auc_roc", sa.Numeric(5, 4), nullable=False),
        sa.Column("f1_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("precision", sa.Numeric(5, 4), nullable=False),
        sa.Column("recall", sa.Numeric(5, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("trained_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("training_data_path", sa.String(512), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["trained_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_tag"),
    )

    # 🔥 Only ONE active model (DB-level constraint)
    op.execute(
        "CREATE UNIQUE INDEX uix_model_versions_active ON model_versions (is_active) "
        "WHERE is_active = TRUE"
    )

    # ── PREDICTION JOBS ──────────────────────────────────────────────────
    op.create_table(
        "prediction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_path", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_jobs_user_status", "prediction_jobs", ["user_id", "status"])
    op.create_index("ix_prediction_jobs_created_at", "prediction_jobs", ["created_at"])

    # ── AUDIT LOGS ───────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(128), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("prediction_result", postgresql.JSONB(), nullable=True),
        sa.Column("model_version_tag", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_input_hash", "audit_logs", ["input_hash"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("prediction_jobs")
    op.drop_table("model_versions")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS audit_action")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS user_role")