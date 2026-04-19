"""
app/core/drift.py — Data and model drift detection engine.

Implements PSI (Population Stability Index) and KS test for Phase 4.

PSI interpretation:
  < 0.10 → No significant change
  0.10–0.20 → Moderate shift — monitor
  > 0.20 → Significant drift — retrain

KS test: p < 0.05 → distributions are statistically different.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

# ── Thresholds ─────────────────────────────────────────────────────────────────

PSI_MODERATE_THRESHOLD = 0.10
PSI_SEVERE_THRESHOLD = 0.20
KS_PVALUE_THRESHOLD = 0.05

# Numeric features tracked for drift (subset most predictive)
TRACKED_NUMERIC_FEATURES = [
    "account_length",
    "number_vmail_messages",
    "total_day_minutes",
    "total_day_charge",
    "total_eve_minutes",
    "total_eve_charge",
    "total_night_minutes",
    "total_intl_minutes",
    "total_intl_calls",
    "customer_service_calls",
]

TRACKED_CATEGORICAL_FEATURES = [
    "international_plan",
    "voice_mail_plan",
]


# ── Result types ───────────────────────────────────────────────────────────────

@dataclass
class FeatureDriftResult:
    feature: str
    psi: float | None
    ks_statistic: float | None
    ks_pvalue: float | None
    drift_detected: bool
    severity: str  # "none" | "moderate" | "severe"
    train_mean: float | None = None
    live_mean: float | None = None
    train_std: float | None = None
    live_std: float | None = None


@dataclass
class DriftReport:
    feature_results: list[FeatureDriftResult]
    overall_drift_score: float  # mean PSI across numeric features
    drift_detected: bool
    drifted_feature_count: int
    severity: str  # "none" | "moderate" | "severe"
    sample_size_train: int
    sample_size_live: int
    computed_at: str = ""


# ── PSI computation ────────────────────────────────────────────────────────────

def _compute_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    bins: int = 10,
) -> float:
    """
    Population Stability Index between two numeric distributions.
    Uses equal-width bins across the combined range.
    Epsilon clipping prevents log(0) errors.
    """
    eps = 1e-6
    combined_min = min(float(expected.min()), float(actual.min()))
    combined_max = max(float(expected.max()), float(actual.max()))

    if combined_min == combined_max:
        return 0.0

    breakpoints = np.linspace(combined_min, combined_max, bins + 1)

    exp_counts = np.histogram(expected, bins=breakpoints)[0]
    act_counts = np.histogram(actual, bins=breakpoints)[0]

    exp_pct = exp_counts / max(len(expected), 1)
    act_pct = act_counts / max(len(actual), 1)

    exp_pct = np.clip(exp_pct, eps, None)
    act_pct = np.clip(act_pct, eps, None)

    psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return round(psi, 6)


def _compute_categorical_psi(
    expected: list[str],
    actual: list[str],
) -> float:
    """PSI for categorical features using category frequencies."""
    eps = 1e-6
    categories = set(expected) | set(actual)
    exp_total = max(len(expected), 1)
    act_total = max(len(actual), 1)

    psi = 0.0
    for cat in categories:
        exp_pct = max(expected.count(cat) / exp_total, eps)
        act_pct = max(actual.count(cat) / act_total, eps)
        psi += (act_pct - exp_pct) * np.log(act_pct / exp_pct)

    return round(float(psi), 6)


# ── Feature-level drift ────────────────────────────────────────────────────────

def compute_numeric_feature_drift(
    train_values: list[float],
    live_values: list[float],
    feature_name: str,
) -> FeatureDriftResult:
    """PSI + KS test for a single numeric feature."""
    if len(train_values) < 10 or len(live_values) < 10:
        return FeatureDriftResult(
            feature=feature_name,
            psi=None,
            ks_statistic=None,
            ks_pvalue=None,
            drift_detected=False,
            severity="none",
        )

    train_arr = np.array(train_values, dtype=float)
    live_arr = np.array(live_values, dtype=float)

    psi = _compute_psi(train_arr, live_arr)
    ks_stat, ks_pvalue = stats.ks_2samp(train_arr, live_arr)
    ks_stat = float(ks_stat)
    ks_pvalue = float(ks_pvalue)

    drift_detected = psi > PSI_MODERATE_THRESHOLD or ks_pvalue < KS_PVALUE_THRESHOLD

    if psi > PSI_SEVERE_THRESHOLD:
        severity = "severe"
    elif psi > PSI_MODERATE_THRESHOLD:
        severity = "moderate"
    else:
        severity = "none"

    return FeatureDriftResult(
        feature=feature_name,
        psi=psi,
        ks_statistic=round(ks_stat, 6),
        ks_pvalue=round(ks_pvalue, 6),
        drift_detected=drift_detected,
        severity=severity,
        train_mean=round(float(train_arr.mean()), 4),
        live_mean=round(float(live_arr.mean()), 4),
        train_std=round(float(train_arr.std()), 4),
        live_std=round(float(live_arr.std()), 4),
    )


def compute_drift_report(
    train_feature_stats: dict[str, list[float]],
    live_feature_stats: dict[str, list[float]],
    computed_at: str = "",
) -> DriftReport:
    """
    Full drift report comparing training distribution vs live prediction inputs.

    Args:
        train_feature_stats: {feature_name: [values...]} from training data
        live_feature_stats: {feature_name: [values...]} from recent predictions
        computed_at: ISO timestamp string

    Returns:
        DriftReport with per-feature results and overall summary
    """
    results: list[FeatureDriftResult] = []
    psi_scores: list[float] = []

    common_features = set(train_feature_stats.keys()) & set(live_feature_stats.keys())

    for feature in TRACKED_NUMERIC_FEATURES:
        if feature not in common_features:
            continue
        result = compute_numeric_feature_drift(
            train_values=train_feature_stats[feature],
            live_values=live_feature_stats[feature],
            feature_name=feature,
        )
        results.append(result)
        if result.psi is not None:
            psi_scores.append(result.psi)

    overall_score = float(np.mean(psi_scores)) if psi_scores else 0.0
    drifted_count = sum(1 for r in results if r.drift_detected)
    any_severe = any(r.severity == "severe" for r in results)
    any_moderate = any(r.severity == "moderate" for r in results)

    if any_severe:
        overall_severity = "severe"
    elif any_moderate:
        overall_severity = "moderate"
    else:
        overall_severity = "none"

    train_size = max(len(v) for v in train_feature_stats.values()) if train_feature_stats else 0
    live_size = max(len(v) for v in live_feature_stats.values()) if live_feature_stats else 0

    return DriftReport(
        feature_results=results,
        overall_drift_score=round(overall_score, 6),
        drift_detected=drifted_count > 0,
        drifted_feature_count=drifted_count,
        severity=overall_severity,
        sample_size_train=train_size,
        sample_size_live=live_size,
        computed_at=computed_at,
    )


# ── Dataset fingerprinting ─────────────────────────────────────────────────────

def compute_dataset_hash(stats: dict[str, Any]) -> str:
    """SHA-256 fingerprint of training dataset statistics. First 16 hex chars."""
    serialized = json.dumps(stats, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def extract_feature_stats_from_df(df: Any) -> dict[str, dict[str, float]]:
    """
    Extract per-feature summary statistics from a pandas DataFrame.
    Returns dict suitable for storing in model metadata.
    """
    stats_dict: dict[str, dict[str, float]] = {}
    for col in TRACKED_NUMERIC_FEATURES:
        if col in df.columns:
            series = df[col].dropna()
            stats_dict[col] = {
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
                "p25": float(series.quantile(0.25)),
                "p50": float(series.quantile(0.50)),
                "p75": float(series.quantile(0.75)),
                "count": int(len(series)),
            }
    return stats_dict
