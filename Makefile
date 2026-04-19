.PHONY: up down build logs train test shell-backend shell-frontend

# ── Start full stack ──────────────────────────────────────────────────────────
up:
	docker compose up --build

up-d:
	docker compose up --build -d

# ── Stop everything ───────────────────────────────────────────────────────────
down:
	docker compose down --remove-orphans

down-v:
	docker compose down --remove-orphans -v

# ── Logs ─────────────────────────────────────────────────────────────────────
logs:
	docker compose logs -f app frontend

logs-all:
	docker compose logs -f

# ── Train ML model ────────────────────────────────────────────────────────────
train:
	docker compose exec app python -m app.ml.train \
		--data-path data/train.csv \
		--output v1 \
		--estimator rf \
		--min-auc 0.75

# ── Run tests ─────────────────────────────────────────────────────────────────
test:
	docker compose exec app pytest tests/unit/ -v

test-all:
	docker compose exec app pytest tests/ -v --cov=app --cov-report=term-missing

# ── Shell access ──────────────────────────────────────────────────────────────
shell-backend:
	docker compose exec app bash

shell-frontend:
	docker compose exec frontend sh

# ── DB migrations ─────────────────────────────────────────────────────────────
migrate:
	docker compose exec app alembic upgrade head

# ── Rebuild single service ────────────────────────────────────────────────────
rebuild-frontend:
	docker compose up --build --force-recreate frontend -d
