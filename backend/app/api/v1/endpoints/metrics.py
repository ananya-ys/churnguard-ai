"""
app/api/v1/endpoints/metrics.py — Prometheus scrape endpoint.

Phase 3: Exposes /metrics for Prometheus scraping.
Also provides /metrics/summary — human-readable JSON for the dashboard.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.metrics import (
    ACTIVE_MODEL_INFO,
    MODEL_AUC_GAUGE,
    MODEL_F1_GAUGE,
)
from app.ml.pipeline import pipeline_manager

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """
    Prometheus scrape endpoint.
    Add this to prometheus.yml targets: http://app:8000/metrics
    """
    # Refresh active model info gauge before scraping
    if pipeline_manager.is_loaded():
        ACTIVE_MODEL_INFO.info({
            "version_tag": pipeline_manager.get_version(),
            "status": "loaded",
        })

    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@router.get("/api/v1/metrics/summary")
async def metrics_summary() -> dict:
    """
    JSON summary of current system metrics.
    Used by the React dashboard — no Prometheus required on frontend.
    """
    from prometheus_client import REGISTRY

    summary: dict = {
        "model_version": pipeline_manager.get_version(),
        "model_loaded": pipeline_manager.is_loaded(),
        "metrics": {},
    }

    # Collect key gauge values from registry
    try:
        for metric in REGISTRY.collect():
            if metric.name in (
                "churnguard_churn_rate_realtime",
                "churnguard_overall_drift_score",
                "churnguard_model_auc_roc",
                "churnguard_model_f1_score",
            ):
                for sample in metric.samples:
                    key = f"{metric.name}__{sample.labels}"
                    summary["metrics"][metric.name] = round(sample.value, 6)
                    break  # take first sample per metric

        # Prediction counter totals
        for metric in REGISTRY.collect():
            if metric.name == "churnguard_predictions_total":
                total = sum(s.value for s in metric.samples)
                summary["metrics"]["total_predictions"] = int(total)
            if metric.name == "churnguard_batch_jobs_total":
                by_status: dict = {}
                for s in metric.samples:
                    status = s.labels.get("status", "unknown")
                    by_status[status] = int(s.value)
                summary["metrics"]["batch_jobs"] = by_status
    except Exception:
        pass

    return summary
