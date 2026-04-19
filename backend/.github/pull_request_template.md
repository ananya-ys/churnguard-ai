## Summary
<!-- One sentence: what does this PR do? -->

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] CI / Infra
- [ ] Docs

---

## Checklist (all required before merge)

### Architecture
- [ ] **PRD link**: <!-- docs/prd/project*.md -->
- [ ] **ADR ref**: <!-- adr/ADR-XXX.md — or "N/A, no new decisions" -->
- [ ] **Layer boundaries respected**: Router → Service → Repository → DB. No business logic in routers or repositories.
- [ ] **No N+1 queries**: All new queries use `joinedload` or explicit joins. EXPLAIN ANALYZE run if new index added.

### Database
- [ ] **Migration included**: Every model change has an Alembic migration.
- [ ] **Migration tested**: `alembic upgrade head` + `alembic downgrade -1` both pass.
- [ ] **SELECT FOR UPDATE**: Used on all state transitions (job status, model promotion).

### Security
- [ ] **RBAC enforced**: Every new route has `Depends(require_role(...))` or `Depends(get_current_active_user)`.
- [ ] **No secrets committed**: `detect-secrets scan` clean.
- [ ] **Input validated**: All new inputs go through Pydantic v2 schema with constraints.

### Testing
- [ ] **Unit tests added**: New logic has unit test coverage.
- [ ] **Integration tests added**: New endpoints have integration tests.
- [ ] **Coverage**: `pytest --cov` still passes 80% threshold.
- [ ] **10/10 concurrency**: `tests/concurrency/` passes locally.

### Observability
- [ ] **Structured logs added**: New service paths log with `structlog` including relevant context fields.
- [ ] **SLO impact**: <!-- Describe effect on p95 latency. "No impact" is acceptable with reasoning. -->

### Deployment
- [ ] **Rollback plan**: <!-- How do we revert if this breaks in production? -->
- [ ] **Docker build passes**: `docker build .` completes successfully.
- [ ] **Environment variables**: Any new env vars added to `.env.example`.

---

## Screenshots / Evidence
<!-- Paste test output, curl responses, or benchmark results. -->
