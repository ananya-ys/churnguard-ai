# ChurnGuard AI — Frontend

React + Vite dashboard for the ChurnGuard AI prediction platform.

## Local Development

```bash
npm install
cp .env.example .env        # set VITE_API_URL=http://localhost:8000
npm run dev                  # runs on http://localhost:5173
```

Make sure the backend is running: `docker compose up` in the backend directory.

## Deploy Frontend to Netlify

1. Push this folder to a GitHub repo
2. Go to [netlify.com](https://netlify.com) → New site from Git
3. Select your repo
4. Build command: `npm run build`
5. Publish directory: `dist`
6. Add environment variable: `VITE_API_URL=https://your-backend-url.onrender.com`
7. Deploy

## Deploy Backend to Render

1. Push the backend folder to a separate GitHub repo
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your backend repo
4. Set environment to **Docker**
5. Add all env vars from `.env.example` (set `DATABASE_URL`, `REDIS_URL` etc)
6. Render provides free PostgreSQL and Redis add-ons
7. Copy the Render URL → paste into Netlify env var `VITE_API_URL`

## Deploy Frontend to Firebase

```bash
npm install -g firebase-tools
npm run build
firebase login
firebase init hosting   # set public dir to "dist", configure as SPA
firebase deploy
```

## Pages

| Route | Description |
|---|---|
| `/` | Dashboard — system health, active model metrics, quick actions |
| `/predict` | Real-time prediction form for a single customer |
| `/batch` | CSV upload for batch predictions |
| `/models` | Model registry — promote, rollback |
| `/jobs` | Batch job status with auto-polling |
| `/login` | Auth — login and register |
