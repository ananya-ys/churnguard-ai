# ADR-001: Stack Decisions for ChurnGuard AI

**Date**: 2026-02-01
**Status**: Accepted
**Author**: Aaryan Raj

---

## Context

ChurnGuard AI is a customer churn prediction SaaS platform requiring real-time inference (<200ms p95), batch CSV processing (50K+ rows), ML model lifecycle management, and a full audit trail for compliance.

---

## Decisions

### 1. FastAPI over Django/Flask
**Decision**: FastAPI 0.115+
**Rationale**: Native async, automatic OpenAPI docs, first-class Pydantic v2 integration, dependency injection system. Django is sync-first with heavy ORM coupling. Flask lacks validation and DI.
**Rejected**: Django REST Framework (sync overhead), Flask (no built-in validation).

### 2. PostgreSQL over MongoDB
**Decision**: PostgreSQL 16
**Rationale**: ACID guarantees required for audit log append-only semantics and model promotion atomicity. Partial unique index (`WHERE is_active=TRUE`) enforces exactly-one-active-model at DB level — impossible in MongoDB. JSONB available for `prediction_result` column when document storage is needed.
**Rejected**: MongoDB (no partial unique indexes, eventual consistency).

### 3. SQLAlchemy Async 2.0 over raw asyncpg or Django ORM
**Decision**: SQLAlchemy 2.0 with asyncpg driver
**Rationale**: Type-safe ORM with Mapped columns, async session management, Alembic migration integration, `SELECT FOR UPDATE` support for state transitions.
**Rejected**: Raw asyncpg (no migration story, no ORM), Django ORM (sync).

### 4. Argon2 over bcrypt
**Decision**: passlib[argon2]
**Rationale**: Argon2 is memory-hard. A GPU can compute ~100M bcrypt hashes/sec but only ~1,000 Argon2 hashes/sec. Orders of magnitude more brute-force resistant. Winner of Password Hashing Competition (2015).
**Rejected**: bcrypt (GPU-breakable at scale), MD5/SHA (never acceptable for passwords).

### 5. Celery + Redis over asyncio background tasks
**Decision**: Celery 5 with Redis 7 broker
**Rationale**: A 50K-row CSV takes 30s+ to process. FastAPI BackgroundTasks share the event loop — a crash kills the task and loses progress. Celery workers are isolated processes with retry logic, progress tracking, and the Beat scheduler for weekly retraining. Redis provides the broker and result backend.
**Rejected**: FastAPI BackgroundTasks (no retry, no persistence), RQ (less feature-complete).

### 6. Singleton PipelineManager with threading.Lock
**Decision**: Module-level singleton with `threading.Lock` for swap
**Rationale**: `joblib.load()` on a large sklearn pipeline takes 1-5 seconds. Per-request loading is unacceptable. Singleton loads once at startup. `swap()` uses `threading.Lock` for atomic, zero-downtime model promotion — no requests are dropped or served stale predictions during swap.
**Rejected**: Per-request load (latency), process restart for model update (downtime).

### 7. Partial unique index for model_version.is_active
**Decision**: `CREATE UNIQUE INDEX WHERE is_active = TRUE`
**Rationale**: Database-level guarantee that exactly one model version is active at any time. Application-level mutex is insufficient — a race condition between two simultaneous promotions could activate two models. The partial index makes that physically impossible.

### 8. Append-only audit log
**Decision**: No UPDATE or DELETE methods on AuditLogRepository
**Rationale**: Mutable audit logs can be altered after the fact — inadmissible for compliance. Every prediction permanently recorded with `input_hash`, model version, and latency. `input_hash` index enables O(1) deduplication.

---

## Rejected Technologies (Global)

| Technology | Reason |
|---|---|
| LangChain | Abstracts away understanding, hard to debug, changes API constantly |
| MongoDB | No partial unique indexes, no ACID for state machines |
| Selenium | Slow, fragile, no CDP. Use Playwright |
| Django/Flask | Sync-first, wrong tool for async ML serving |
| Serverless | Cold start latency incompatible with p95 ≤ 200ms SLO |
| Notebooks for ML | Not version-controlled, not reproducible in CI |
