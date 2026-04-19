"""app/api/v1/router.py — API v1 router with all phases wired in."""

from fastapi import APIRouter

from app.api.v1.endpoints import audit_logs, auth, jobs, models, predict, upload
from app.api.v1.endpoints import experiments, drift, explain, ab_tests

api_router = APIRouter(prefix="/api/v1")

# ── Existing endpoints ─────────────────────────────────────────────────────────
api_router.include_router(auth.router)
api_router.include_router(predict.router)
api_router.include_router(upload.router)
api_router.include_router(jobs.router)
api_router.include_router(models.router)
api_router.include_router(audit_logs.router)

# ── Phase 2: ML Lifecycle ─────────────────────────────────────────────────────
api_router.include_router(experiments.router)

# ── Phase 4: Drift monitoring ─────────────────────────────────────────────────
api_router.include_router(drift.router)

# ── Phase 6: Explainability + A/B Testing ─────────────────────────────────────
api_router.include_router(explain.router)
api_router.include_router(ab_tests.router)
