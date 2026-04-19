# ChurnGuard AI

**Customer Churn Prediction SaaS Platform**
FastAPI · scikit-learn · PostgreSQL 16 · Redis 7 · Celery · Docker

[![CI](https://github.com/your-org/churnguard-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/churnguard-ai/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/your-org/churnguard-ai/badge.svg)](https://codecov.io/gh/your-org/churnguard-ai)

---

## Architecture

```
CLIENT
  │
API GATEWAY       JWT Auth · Rate Limiter (slowapi) · CORS · Request-ID
  │
FASTAPI ROUTER    POST /predict · POST /upload · GET /jobs/{id} · /models · /auth/*
  │
SERVICE LAYER     predict_service · batch_service · model_service · auth_service · audit_service
  │
REPOSITORY LAYER  user_repo · prediction_job_repo · model_version_repo · audit_log_repo
  │
DATABASE          PostgreSQL 16 (ACID) · Redis 7 (cache + queue)
  │
ASYNC WORKERS     Celery: batch_predict · retrain (weekly, AUC gate)
```

**Layer contract**: Router → Service → Repository → DB. No business logic in routers or repositories. Violations blocked in code review.

---

## Quick Start (< 5 minutes)

### Prerequisites
- Docker + Docker Compose
- Python 3.11+

### 1. Clone and configure

```bash
git clone https://github.com/your-org/churnguard-ai
cd churnguard-ai
cp .env.example .env
# Edit .env — set a real SECRET_KEY (32+ chars)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Start full stack

```bash
docker compose up --build
```

This starts: PostgreSQL · Redis · Migrations · FastAPI app · Celery worker · Celery Beat · Flower

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"ok","redis":"ok","model_loaded":false}

curl http://localhost:8000/docs  # Swagger UI
```

### 4. Train and register a model

```bash
# Generate sample data first (or use your own telecom CSV)
python -m app.ml.train \
  --data-path data/train.csv \
  --output v1 \
  --estimator rf \
  --min-auc 0.75

# Register via API
curl -X POST http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version_tag":"v1","artifact_path":"app/ml/artifacts/v1.pkl",
       "auc_roc":0.88,"f1_score":0.82,"precision":0.85,"recall":0.80}'

# Promote
curl -X POST http://localhost:8000/api/v1/models/{id}/promote \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 5. Make a prediction

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "records": [{
      "state": "CA", "account_length": 120, "area_code": 415,
      "international_plan": "no", "voice_mail_plan": "yes",
      "number_vmail_messages": 25, "total_day_minutes": 265.1,
      "total_day_calls": 110, "total_day_charge": 45.07,
      "total_eve_minutes": 197.4, "total_eve_calls": 99, "total_eve_charge": 16.78,
      "total_night_minutes": 244.7, "total_night_calls": 91, "total_night_charge": 11.01,
      "total_intl_minutes": 10.0, "total_intl_calls": 3, "total_intl_charge": 2.70,
      "customer_service_calls": 1
    }]
  }'
```

---

## Running Tests

```bash
pip install -r requirements.txt

# Unit tests only (no DB required)
pytest tests/unit/ -v

# Full suite (requires PostgreSQL + Redis)
pytest tests/ --cov=app --cov-report=term-missing

# Concurrency tests (50 parallel requests)
pytest tests/concurrency/ -v

# Smoke tests against running instance
SMOKE_BASE_URL=http://localhost:8000 pytest tests/smoke/ -v
```

---

## Phase Gates

| Phase | Gate | Status |
|---|---|---|
| 0 — Foundation | GET /health 200, DB + Redis confirmed | ✅ |
| 1 — Auth + RBAC | Register → login → /me → 401/403 correct | ✅ |
| 2 — Domain Models | 4 tables migrated, all repos tested | ✅ |
| 3 — Core Logic | /predict p95 ≤ 200ms, 50/50 concurrency | ✅ |
| 4 — Batch Engine | Upload → QUEUED → PROCESSING → COMPLETED | ✅ |
| 5 — Model Registry | Register → AUC gate → promote → rollback | ✅ |
| 6 — Audit Log | Append-only, no UPDATE/DELETE methods | ✅ |
| 7 — Advanced | Redis cache, rate limiting, scheduled retrain | ✅ |
| 8 — Testing | >80% coverage, 50/50 concurrency passes | ✅ |
| 9 — CI/CD | lint → test → Trivy → Docker build → GHCR | ✅ |

---

## SLO Table

| Endpoint | p50 | p95 | p99 |
|---|---|---|---|
| GET /health | < 10ms | < 50ms | < 100ms |
| POST /api/v1/auth/login | < 100ms | < 200ms | < 500ms |
| POST /api/v1/predict (1 record) | < 20ms | < 200ms | < 500ms |
| POST /api/v1/predict (500 records) | < 200ms | < 500ms | < 1000ms |
| POST /api/v1/upload | < 50ms | < 200ms | < 500ms |
| GET /api/v1/jobs/{id} | < 10ms | < 50ms | < 100ms |

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| POST /predict | 100/min (API_USER), 1000/min (ANALYST+) |
| POST /upload | 10/hour per user |
| POST /auth/login | 5/min (brute-force guard) |

---

## Security

- Argon2 password hashing (memory-hard, GPU-resistant)
- JWT auth with short expiry (60 min default)
- Zero-trust RBAC: role re-verified from DB on every request
- Append-only audit log (no UPDATE/DELETE on audit table)
- Partial unique index: one active model at a time (DB-level guarantee)
- Trivy CVE scan blocks HIGH/CRITICAL on every PR
- detect-secrets blocks any committed secret on every PR
- Non-root container user (`churnguard`, UID 1000)
- CORS restricted to configured origins (never `*` in production)

---

## Project Structure

```
app/
├── core/          config, database, security, logging, cache, middleware, exceptions
├── models/        user, prediction_job, model_version, audit_log (SQLAlchemy ORM)
├── schemas/       auth, predict, batch, model_version, common (Pydantic v2)
├── repositories/  user, prediction_job, model_version, audit_log (DB access only)
├── services/      auth, predict, batch, model, audit (all business logic)
├── api/v1/        endpoints: auth, predict, upload, jobs, models, audit_logs, health
├── dependencies/  auth.py (JWT + RBAC), db.py (session injection)
├── ml/            pipeline.py (singleton), train.py (AUC gate CLI)
└── tasks/         worker.py, batch_predict.py, retrain.py (all idempotent)
```

---

## Celery Monitor

Flower UI available at `http://localhost:5555` — view active workers, task history, queue depth.

---

## ADRs

- [ADR-001: Stack Decisions](docs/adr/ADR-001-stack-decisions.md)

## Runbooks

- [On-Call Runbook](runbooks/on-call.md)
