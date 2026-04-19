import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.database import Base
from app.models.ab_test import ABTest  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.drift_report import DriftReport  # noqa: F401
from app.models.experiment import ExperimentRun  # noqa: F401
from app.models.model_version import ModelVersion  # noqa: F401
from app.models.prediction_job import PredictionJob  # noqa: F401
from app.models.user import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("SYNC_DATABASE_URL", "")
    if not url:
        url = os.getenv("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
    return url or config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
