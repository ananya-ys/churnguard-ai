"""app/schemas/experiment.py — Pydantic schemas for experiments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExperimentRunResponse(BaseModel):
    id: uuid.UUID
    run_id: str
    version_tag: str
    estimator_key: str
    dataset_path: str
    dataset_hash: str
    dataset_row_count: int
    git_commit: str
    git_branch: str
    triggered_by: str
    hyperparameters: dict | None
    metrics: dict | None
    feature_importance: dict | None
    duration_seconds: float
    auc_gate_passed: bool
    promoted: bool
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperimentCompareRequest(BaseModel):
    run_id_a: str
    run_id_b: str


class MetricComparison(BaseModel):
    metric: str
    value_a: float
    value_b: float
    delta: float
    winner: str  # "a" | "b" | "tie"


class ExperimentCompareResponse(BaseModel):
    run_a: ExperimentRunResponse
    run_b: ExperimentRunResponse
    metric_comparisons: list[MetricComparison]
    overall_winner: str
