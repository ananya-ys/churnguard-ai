# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN useradd -m -u 1000 churnguard

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# 🔥 IMPORTANT FIX
ENV PYTHONPATH=/app

COPY --chown=churnguard:churnguard app/ ./app/
COPY --chown=churnguard:churnguard alembic/ ./alembic/
COPY --chown=churnguard:churnguard alembic.ini ./
COPY --chown=churnguard:churnguard pyproject.toml ./
COPY --chown=churnguard:churnguard tests/ ./tests/
COPY --chown=churnguard:churnguard data/ ./data/

RUN mkdir -p /tmp/churnguard/uploads app/ml/artifacts \
    && chown -R churnguard:churnguard /tmp/churnguard app/ml/artifacts

USER churnguard

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]