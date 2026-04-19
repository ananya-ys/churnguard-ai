# ChurnGuard AI — On-Call Runbook

**Stack**: FastAPI · PostgreSQL 16 · Redis 7 · Celery · Docker
**Repo**: github.com/your-org/churnguard-ai

---

## Alert: /health returns `degraded`

**Triage order:**
1. Check `database` field — if `"error"`: PostgreSQL is unreachable.
2. Check `redis` field — if `"error"`: Redis is unreachable.
3. Check `model_loaded` — if `false`: pipeline file missing or failed to load.

**Fix — DB unreachable:**
```bash
docker compose ps postgres          # Is it running?
docker compose logs postgres        # Check for OOM or disk full
docker compose restart postgres
```

**Fix — Redis unreachable:**
```bash
docker compose ps redis
docker compose restart redis
```

**Fix — Model not loaded:**
```bash
# Verify artifact exists
ls -lh app/ml/artifacts/

# Re-register and promote a known-good version
curl -X POST /api/v1/models \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"version_tag":"v1","artifact_path":"app/ml/artifacts/v1.pkl","auc_roc":0.88,...}'
curl -X POST /api/v1/models/{id}/promote -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Alert: Celery workers not processing jobs

**Symptoms**: Jobs stuck in `QUEUED` status for > 5 minutes.

```bash
# Check worker status
docker compose logs celery_worker --tail=50

# Check Redis broker queue depth
docker compose exec redis redis-cli LLEN celery

# Restart worker
docker compose restart celery_worker

# If jobs are poisoned (permanently PROCESSING after restart):
# Manually set failed via psql
psql $DATABASE_URL -c "
  UPDATE prediction_jobs
  SET status='failed', error_message='Worker crashed — manual recovery'
  WHERE status='processing'
    AND started_at < NOW() - INTERVAL '30 minutes';"
```

---

## Alert: p95 latency > 200ms on POST /predict

**Triage:**
```bash
# Check slow queries
psql $DATABASE_URL -c "SELECT query, mean_exec_time, calls
  FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check connection pool saturation
psql $DATABASE_URL -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Profile with py-spy (attach to running container)
docker compose exec app pip install py-spy
docker compose exec app py-spy top --pid 1
```

**Common fixes:**
- N+1 query introduced: add `joinedload` to repository query.
- Pool exhaustion: increase `DB_POOL_SIZE` in `.env`, redeploy.
- Model predict_proba slow: profile with scalene, check if model needs retrain on smaller feature set.

---

## Alert: AUC gate failed on scheduled retrain

**What happened**: Weekly retrain produced a model below 0.75 AUC. Production model is unchanged.

```bash
# Check audit log for retrain_fail entry
psql $DATABASE_URL -c "
  SELECT created_at, model_version_tag, entity_id
  FROM audit_logs WHERE action='retrain_fail'
  ORDER BY created_at DESC LIMIT 5;"

# Check Celery logs for training error details
docker compose logs celery_beat --tail=100

# Manually retrain with more data or different estimator
python -m app.ml.train \
  --data-path data/train_extended.csv \
  --output v-recovery \
  --estimator gbm \
  --min-auc 0.75
```

---

## Rollback — bad model in production

```bash
# Via API (preferred — atomic, audited)
curl -X POST /api/v1/models/rollback \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify rollback
curl /api/v1/models/active -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Rollback — bad deployment

```bash
# Re-deploy previous image (tagged with git SHA)
docker pull ghcr.io/your-org/churnguard-ai:$PREVIOUS_SHA
docker tag ghcr.io/your-org/churnguard-ai:$PREVIOUS_SHA \
           ghcr.io/your-org/churnguard-ai:latest
docker compose up -d app

# Verify health
curl http://localhost:8000/health
```

---

## Rate limit verification

```bash
# 6th login in 1 minute should return 429
for i in {1..6}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/v1/auth/login \
    -d "username=test@test.com&password=wrong"
done
# Expected: 401 401 401 401 401 429
```

---

## Database backup

```bash
# Manual backup
docker compose exec postgres pg_dump -U churnguard churnguard \
  | gzip > backup_$(date +%Y%m%d_%H%M).sql.gz

# Restore
gunzip -c backup_YYYYMMDD_HHMM.sql.gz \
  | docker compose exec -T postgres psql -U churnguard churnguard
```
