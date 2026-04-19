"""
app/core/metrics.py — Prometheus metrics registry.

Singleton counters/histograms/gauges registered once at import time.
Import this module anywhere to record metrics — no re-registration errors.

Phase 3 deliverable: prediction latency, API counters, model usage, drift scores.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ── Prediction metrics ─────────────────────────────────────────────────────────

PREDICTION_COUNTER = Counter(
    "churnguard_predictions_total",
    "Total number of predictions made",
    ["model_version", "confidence_band"],
)

PREDICTION_LATENCY = Histogram(
    "churnguard_prediction_latency_seconds",
    "End-to-end prediction latency in seconds",
    ["model_version"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0],
)

CHURN_PROBABILITY_HISTOGRAM = Histogram(
    "churnguard_churn_probability_distribution",
    "Distribution of predicted churn probabilities",
    ["model_version"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

CHURN_RATE_GAUGE = Gauge(
    "churnguard_churn_rate_realtime",
    "Rolling churn rate (fraction) from recent predictions",
    ["model_version"],
)

# ── Model registry metrics ─────────────────────────────────────────────────────

ACTIVE_MODEL_INFO = Info(
    "churnguard_active_model",
    "Metadata of the currently active model",
)

MODEL_AUC_GAUGE = Gauge(
    "churnguard_model_auc_roc",
    "AUC-ROC score for a given model version",
    ["version_tag"],
)

MODEL_F1_GAUGE = Gauge(
    "churnguard_model_f1_score",
    "F1 score for a given model version",
    ["version_tag"],
)

MODEL_PROMOTIONS_COUNTER = Counter(
    "churnguard_model_promotions_total",
    "Total model promotions",
    ["version_tag"],
)

MODEL_ROLLBACKS_COUNTER = Counter(
    "churnguard_model_rollbacks_total",
    "Total model rollbacks",
)

# ── API metrics ────────────────────────────────────────────────────────────────

HTTP_REQUEST_COUNTER = Counter(
    "churnguard_http_requests_total",
    "Total HTTP requests by method, endpoint, and status",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_LATENCY = Histogram(
    "churnguard_http_request_latency_seconds",
    "HTTP request latency by method and endpoint",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

HTTP_ERROR_COUNTER = Counter(
    "churnguard_http_errors_total",
    "Total HTTP 5xx errors",
    ["endpoint"],
)

# ── Batch job metrics ──────────────────────────────────────────────────────────

BATCH_JOB_COUNTER = Counter(
    "churnguard_batch_jobs_total",
    "Total batch prediction jobs by final status",
    ["status"],  # queued | completed | failed
)

BATCH_ROWS_PROCESSED_COUNTER = Counter(
    "churnguard_batch_rows_processed_total",
    "Total customer rows processed in batch jobs",
    ["model_version"],
)

BATCH_JOB_LATENCY = Histogram(
    "churnguard_batch_job_duration_seconds",
    "Batch job end-to-end duration in seconds",
    buckets=[1, 5, 15, 30, 60, 120, 300, 600],
)

# ── Drift metrics ──────────────────────────────────────────────────────────────

DRIFT_PSI_GAUGE = Gauge(
    "churnguard_drift_psi_score",
    "Population Stability Index per feature",
    ["feature"],
)

DRIFT_KS_PVALUE_GAUGE = Gauge(
    "churnguard_drift_ks_pvalue",
    "KS test p-value per feature (< 0.05 = drift)",
    ["feature"],
)

DRIFT_ALERTS_COUNTER = Counter(
    "churnguard_drift_alerts_total",
    "Total drift alerts triggered",
    ["feature", "severity"],
)

OVERALL_DRIFT_SCORE_GAUGE = Gauge(
    "churnguard_overall_drift_score",
    "Mean PSI across all tracked numeric features",
)

# ── A/B testing metrics ────────────────────────────────────────────────────────

AB_TEST_REQUEST_COUNTER = Counter(
    "churnguard_ab_test_requests_total",
    "Total requests routed per A/B test variant",
    ["experiment_name", "variant"],
)

AB_TEST_CHURN_RATE_GAUGE = Gauge(
    "churnguard_ab_test_churn_rate",
    "Realtime churn rate per A/B test variant",
    ["experiment_name", "variant"],
)

# ── Auth/security metrics ──────────────────────────────────────────────────────

AUTH_LOGIN_COUNTER = Counter(
    "churnguard_auth_logins_total",
    "Total login attempts",
    ["status"],  # success | failure
)

AUTH_RATE_LIMIT_COUNTER = Counter(
    "churnguard_rate_limit_hits_total",
    "Total rate limit rejections by endpoint",
    ["endpoint"],
)
