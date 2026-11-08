# Creator Studio AI — Staging & Production Deployment Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Hosting Strategy:** Strictly $0.00 / month Zero-Cost Staging Architecture  
**Frontend Host:** GitHub Pages (Static HTML Export)  
**Database Host:** Supabase Free PostgreSQL 15  
**Backend Host:** Local-First FastAPI Daemon & Persistent Queue Worker  

---

## 1. Zero-Cost Staging Deployment Architecture

Creator Studio AI operates on a completely free-tier infrastructure stack:

```
+-------------------------------------------------------------------------+
|                          STAGING TOPOLOGY                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  [USER BROWSER]                                                         |
|         │                                                               |
|         ▼                                                               |
|  GITHUB PAGES (Static HTML Export)                                      |
|  - Hosted at https://alikhan14756.github.io/ai_auto/                    |
|  - Next.js 15.1.0 pre-rendered static artifacts                         |
|  - 0-dollar hosting budget                                              |
|         │                                                               |
|         ▼ (REST API / CORS)                                             |
|  LOCAL FASTAPI BACKEND (Uvicorn on Port 8000)                           |
|  - Running locally or cloud-proxied via ngrok / cloudflared tunnel      |
|  - $0.00 Spend Governor actively enforcing free tiers                   |
|         │                                                               |
|         ├─────────────────────────────────────────┐                     |
|         ▼                                         ▼                     |
|  SUPABASE POSTGRESQL 15                PERSISTENT QUEUE WORKER          |
|  - Free-tier 500MB database            - Local daemon running in loop   |
|  - 52 application tables               - SELECT FOR UPDATE SKIP LOCKED  |
|  - SSL encrypted connections           - FFmpeg rendering & Edge-TTS    |
+-------------------------------------------------------------------------+
```

---

## 2. GitHub Pages Deployment Steps

The GitHub Pages deployment pipeline is automated via GitHub Actions in `.github/workflows/deploy.yml`:

1. Build process runs `npm --prefix frontend run build`.
2. Static assets are exported to `frontend/out/`.
3. A `.nojekyll` file is added to prevent GitHub Pages from bypassing files starting with underscores.
4. The GitHub Pages deployment action publishes the bundle to the `gh-pages` branch.

### Manual Local Export Verification:
```powershell
cd frontend
npm run build
# Inspect generated files in frontend/out
```

---

## 3. Supabase Database Provisioning

1. Create a free account at [supabase.com](https://supabase.com).
2. Create a new project named `creator-studio-ai`.
3. Copy the database connection URI from **Project Settings > Database > Connection Strings**.
4. Set `DATABASE_URL` and `SYNC_DATABASE_URL` in `backend/.env`.
5. Run migrations:
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   alembic upgrade head
   ```

---

## 4. Local Backend & Worker Daemon Startup

To run the backend and queue worker on Windows:

```powershell
# Start FastAPI backend
powershell -File .\scripts\start-backend.ps1

# Start persistent queue worker
powershell -File .\scripts\start-worker.ps1
```

To expose the local backend to your GitHub Pages frontend securely at zero cost:
```powershell
# Using Cloudflare Tunnel (Zero Cost)
cloudflared tunnel --url http://localhost:8000
```
Update `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` to point to the tunnel URL.
