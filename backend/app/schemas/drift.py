"""app/schemas/drift.py — Pydantic schemas for drift + A/B tests."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Drift schemas ───────────────────────────────────────────────────────────────

class FeatureDriftItem(BaseModel):
    feature: str
    psi: float | None
    ks_statistic: float | None
    ks_pvalue: float | None
    drift_detected: bool
    severity: str
    train_mean: float | None
    live_mean: float | None
    train_std: float | None
    live_std: float | None


class DriftReportResponse(BaseModel):
    id: uuid.UUID
    model_version_tag: str
    overall_drift_score: float
    drift_detected: bool
    drifted_feature_count: int
    severity: str
    sample_size_train: int
    sample_size_live: int
    feature_results: list[FeatureDriftItem] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerDriftCheckResponse(BaseModel):
    message: str
    report_id: uuid.UUID
    drift_detected: bool
    severity: str
    overall_drift_score: float
    drifted_feature_count: int


# ── A/B test schemas ────────────────────────────────────────────────────────────

class ABTestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    control_version_tag: str
    treatment_version_tag: str
    treatment_traffic_fraction: float = Field(default=0.5, ge=0.0, le=1.0)


class ABTestStats(BaseModel):
    variant: str
    requests: int
    mean_churn_probability: float | None
    churn_rate_estimate: float | None


class ABTestResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    control_version_tag: str
    treatment_version_tag: str
    treatment_traffic_fraction: float
    is_active: bool
    control_stats: ABTestStats
    treatment_stats: ABTestStats
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ABTestStopResponse(BaseModel):
    message: str
    test_id: uuid.UUID
    winner: str | None
    control_mean_churn: float | None
    treatment_mean_churn: float | None
