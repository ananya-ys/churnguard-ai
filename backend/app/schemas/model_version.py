"""app/schemas/model_version.py — Model version schemas (updated for Phases 1-6)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ModelVersionResponse(BaseModel):
    id: uuid.UUID
    version_tag: str
    artifact_path: str
    auc_roc: float
    f1_score: float
    precision: float
    recall: float
    is_active: bool
    trained_by_id: uuid.UUID | None
    training_data_path: str | None
    row_count: int | None
    dataset_hash: str | None
    estimator_key: str | None
    created_at: datetime
    promoted_at: datetime | None

    model_config = {"from_attributes": True}


class ModelVersionRegister(BaseModel):
    version_tag: str = Field(min_length=1, max_length=64)
    artifact_path: str = Field(min_length=1, max_length=512)
    auc_roc: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    training_data_path: str | None = None
    row_count: int | None = Field(default=None, ge=1)
    # Phase 2: lineage fields (optional for backward compat)
    dataset_hash: str | None = None
    estimator_key: str | None = None
    training_feature_stats: dict | None = None


class ModelPromoteResponse(BaseModel):
    message: str
    version_tag: str
    promoted_at: datetime
