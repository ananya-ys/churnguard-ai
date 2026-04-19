# ChurnGuard AI — Full Stack

Customer Churn Prediction SaaS · FastAPI + React + PostgreSQL + Redis + Celery

```
http://localhost:3000  → React frontend (nginx)
http://localhost:8000  → FastAPI backend
http://localhost:5555  → Flower (Celery monitor)
```

---

## Quick Start (< 5 minutes)

### 1. Clone and configure
```bash
git clone https://github.com/YOUR_USERNAME/churnguard-ai
cd churnguard-ai
cp .env.example .env
```

Open `.env` and set a real `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Paste the output as `SECRET_KEY` in `.env`.

### 2. Start everything
```bash
docker compose up --build
```

This starts: PostgreSQL → Redis → Migrations → FastAPI → Celery Worker + Beat → Flower → React Frontend

Wait ~60 seconds for the first build. On subsequent starts it's ~10 seconds.

### 3. Open the app
```
http://localhost:3000
```

Register an account, login, and explore the dashboard.

### 4. Train and activate the ML model

First, get the dataset:
```bash
mkdir -p backend/data
curl -L "https://raw.githubusercontent.com/dsrscientist/dataset1/master/telecom_churn.csv" \
  -o backend/data/train.csv
```

Train inside the container:
```bash
docker compose exec app python -m app.ml.train \
  --data-path data/train.csv \
  --output v1 \
  --estimator rf \
  --min-auc 0.75
```

Then in the UI: go to **Models** → register v1 → **Promote**. The dashboard will show `model_loaded: true`.

---

## Project Structure

```
churnguard-ai/
├── backend/              FastAPI app
│   ├── app/
│   │   ├── api/          Routers (HTTP only)
│   │   ├── services/     Business logic
│   │   ├── repositories/ DB access
│   │   ├── models/       SQLAlchemy ORM
│   │   ├── schemas/      Pydantic v2
│   │   ├── ml/           Pipeline singleton + training
│   │   └── tasks/        Celery tasks
│   ├── alembic/          Migrations
│   ├── tests/            Unit + integration + concurrency
│   └── Dockerfile
├── frontend/             React + Vite
│   ├── src/
│   │   ├── pages/        Dashboard, Predict, Batch, Models, Jobs, Login
│   │   ├── components/   Layout, Sidebar
│   │   └── api.js        All API calls
│   ├── nginx.conf        Proxies /api → backend
│   └── Dockerfile
├── docker-compose.yml    Single command to run everything
├── .env                  Your local config (not committed)
├── .env.example          Safe template (committed)
└── Makefile              Convenience commands
```

---

## Useful Commands

```bash
make up           # Start full stack (with build)
make up-d         # Start detached
make down         # Stop all containers
make down-v       # Stop + delete volumes (fresh DB)
make logs         # Follow app + frontend logs
make train        # Train ML model
make test         # Run unit tests
make test-all     # Full test suite with coverage
make shell-backend  # bash into FastAPI container
```

---

## Deploy to Cloud (Free Tier)

### Backend → Render

1. Push the whole repo to GitHub
2. [render.com](https://render.com) → New Web Service → connect repo
3. **Root Directory**: `backend`
4. **Runtime**: Docker
5. Add a free **PostgreSQL** and **Redis** from Render dashboard
6. Set all env vars from `.env.example` (use Render's DB + Redis URLs)
7. Add `ALLOWED_ORIGINS=["https://your-netlify-app.netlify.app"]`
8. Copy your Render URL e.g. `https://churnguard-api.onrender.com`

### Frontend → Netlify

1. [netlify.com](https://netlify.com) → New site from Git → connect same repo
2. **Base directory**: `frontend`
3. **Build command**: `npm run build`
4. **Publish directory**: `frontend/dist`
5. Environment variables:
   ```
   VITE_API_URL=https://churnguard-api.onrender.com
   ```
6. Deploy → live URL instantly

### Frontend → Firebase

```bash
cd frontend
npm install
npm run build
npm install -g firebase-tools
firebase login
firebase init hosting    # public dir = dist, SPA = yes
firebase deploy
```

---

## SLO Targets

| Endpoint | p95 target |
|---|---|
| GET /health | < 50ms |
| POST /predict | < 200ms |
| POST /upload | < 200ms (returns job_id immediately) |
| GET /jobs/{id} | < 50ms |

---

## Tech Stack

**Backend**: FastAPI 0.115 · SQLAlchemy 2.0 Async · PostgreSQL 16 · Redis 7 · Celery 5 · scikit-learn 1.5 · Argon2 · JWT

**Frontend**: React 18 · Vite · React Router · Recharts · nginx

**Infra**: Docker multi-stage builds · GitHub Actions CI · Alembic migrations
