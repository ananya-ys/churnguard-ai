from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    docs_url: str | None = "/docs"
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("docs_url", mode="before")
    @classmethod
    def hide_docs_in_prod(cls, v: str | None, info: object) -> str | None:
        # Evaluated at field level; env can override to None for prod
        return v

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(..., pattern=r"^postgresql\+asyncpg://")
    sync_database_url: str = Field(..., pattern=r"^postgresql\+psycopg2://")
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # ── Auth ──────────────────────────────────────────────────────────────────
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # ── ML ────────────────────────────────────────────────────────────────────
    model_path: str = "app/ml/artifacts/v1.pkl"
    min_auc_threshold: float = 0.75
    prediction_batch_size: int = 500
    chunk_size: int = 1000

    # ── Upload ────────────────────────────────────────────────────────────────
    upload_dir: str = "/tmp/churnguard/uploads"
    max_upload_size_mb: int = 50

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # ── Observability ─────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
