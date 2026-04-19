"""
app/main.py — FastAPI application factory with all phases.

Phase 3 additions:
  - PrometheusMiddleware for per-endpoint HTTP metrics
  - /metrics scrape endpoint registered outside API prefix
  - Model info gauge updated on startup

Phase 5: healthcheck updated to reflect full system state.
"""

import time
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.router import api_router
from app.core.cache import close_redis, get_redis
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.metrics import (
    HTTP_ERROR_COUNTER,
    HTTP_REQUEST_COUNTER,
    HTTP_REQUEST_LATENCY,
    MODEL_AUC_GAUGE,
    MODEL_F1_GAUGE,
    AUTH_RATE_LIMIT_COUNTER,
)
from app.ml.pipeline import pipeline_manager

logger = structlog.get_logger(__name__)


# ── Phase 3: Prometheus HTTP middleware ────────────────────────────────────────

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Records HTTP request count, latency, and errors per endpoint.
    Uses normalized path to avoid label cardinality explosion from UUIDs.
    """

    # Normalize dynamic path segments to avoid high cardinality
    _SKIP_PATHS = {"/metrics", "/health", "/favicon.ico"}
    _UUID_PATTERN = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    def _normalize_path(self, path: str) -> str:
        import re
        # Replace UUIDs with placeholder
        normalized = re.sub(self._UUID_PATTERN, "{id}", path)
        # Remove trailing slash
        return normalized.rstrip("/") or "/"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in self._SKIP_PATHS:
            return await call_next(request)

        normalized = self._normalize_path(path)
        method = request.method
        start = time.monotonic()

        response = await call_next(request)

        latency = time.monotonic() - start
        status = str(response.status_code)

        HTTP_REQUEST_COUNTER.labels(
            method=method, endpoint=normalized, status_code=status
        ).inc()
        HTTP_REQUEST_LATENCY.labels(
            method=method, endpoint=normalized
        ).observe(latency)

        if response.status_code >= 500:
            HTTP_ERROR_COUNTER.labels(endpoint=normalized).inc()

        return response


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ────────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("churnguard_starting", env=settings.app_env)

    try:
        r = await get_redis()
        await r.ping()
        logger.info("redis_connected")
    except Exception:
        logger.warning("redis_unavailable_at_startup")

    # Load ML pipeline
    pipeline_manager.load(settings.model_path)
    if pipeline_manager.is_loaded():
        version = pipeline_manager.get_version()
        logger.info("pipeline_loaded", version=version)
        # Update Prometheus model info gauges
        MODEL_AUC_GAUGE.labels(version_tag=version).set(0)  # placeholder — updated by model service
    else:
        logger.warning("pipeline_not_loaded", path=settings.model_path)

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    await close_redis()
    logger.info("churnguard_shutdown")


# ── App factory ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address)

    app = FastAPI(
        title="ChurnGuard AI",
        description=(
            "Customer Churn Prediction SaaS Platform — "
            "Phase 1: Automation | Phase 2: ML Lifecycle | "
            "Phase 3: Observability | Phase 4: Drift | "
            "Phase 5: CI/CD | Phase 6: Differentiators"
        ),
        version="4.0.0",
        docs_url=settings.docs_url,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Rate limiter ───────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── Phase 3: Prometheus middleware ─────────────────────────────────────────
    app.add_middleware(PrometheusMiddleware)

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # ── Request ID + structured access log ────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)

    # ── Error handlers ────────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(metrics_router)  # /metrics (Prometheus scrape)
    app.include_router(api_router)      # /api/v1/...

    return app


app = create_app()
