# CREATOR STUDIO AI — PRODUCTION DEPLOYMENT GUIDE

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**Repository:** [https://github.com/alikhan14756/ai_auto](https://github.com/alikhan14756/ai_auto)  
**Target Environment:** Zero-Cost Cloud SaaS ($0.00/month baseline)

---

## 1. Architecture Overview

Creator Studio AI uses a decoupled client-server architecture designed for high availability and zero operational costs:

```
[ Next.js Frontend ]  ---> HTTPS ---> [ FastAPI Backend ] ---> SSL/PgBouncer ---> [ Supabase PostgreSQL ]
    (Vercel Free)                         (Render / Fly.io)                              (Supabase Free)
                                                |
                                                v
                                      [ Background Worker ]
                                     (FOR UPDATE SKIP LOCKED)
```

- **Frontend:** Next.js 15.5.29 App Router, hosted on Vercel with automatic TLS.
- **Backend:** FastAPI async application hosted on Render, Railway, or Fly.io free tier.
- **Database:** Supabase PostgreSQL with transaction pooling on port 6543 and direct migrations on port 5432.
- **Worker Daemon:** Asynchronous job processor executing durable background tasks from the `automation_jobs` table.

---

## 2. Infrastructure Setup & Prerequisites

### 2.1. Supabase PostgreSQL Setup
1. Create a free project at [supabase.com](https://supabase.com).
2. Retrieve the following credentials from **Project Settings > Database**:
   - **Transaction Pooler URL (IPv4):** Port `6543`, e.g. `postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   - **Direct Connection URL:** Port `5432`, e.g. `postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`
3. Retrieve API keys from **Project Settings > API**:
   - `SUPABASE_URL`: `https://[PROJECT-REF].supabase.co`
   - `SUPABASE_ANON_KEY`: Public client key
   - `SUPABASE_SERVICE_ROLE_KEY`: Secret service role key (backend only)
   - `SUPABASE_JWT_SECRET`: JWT secret for validating authentication tokens

### 2.2. Google Gemini AI API Key
1. Create a free API key at [ai.google.dev](https://ai.google.dev).
2. The key will be used with `gemini-1.5-flash` and `gemini-1.5-pro` under the strict free tier limits (15 requests/min, 1,500 requests/day).

### 2.3. Google Cloud Console (YouTube OAuth 2.0)
1. In the Google Cloud Console, enable **YouTube Data API v3** and **YouTube Analytics API v2**.
2. Configure the OAuth Consent Screen with scopes:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
3. Create OAuth 2.0 Web Application credentials and configure Authorized Redirect URIs:
   - Production: `https://[YOUR-BACKEND-DOMAIN]/api/v1/youtube/oauth/callback`
   - Local: `http://localhost:8000/api/v1/youtube/oauth/callback`

---

## 3. Database Migration Runbook

Before launching the backend, apply all 10 Alembic migrations to create the schema:

```powershell
# In the backend directory:
cd backend
$env:DATABASE_URL_SYNC = "postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require"
.venv\Scripts\alembic upgrade head
```

Verify the migration state:
```powershell
.venv\Scripts\alembic current
# Expected head: 0010_add_workflow_orchestration_and_policies (head)
```

---

## 4. Backend Cloud Deployment (e.g., Render Free Web Service)

1. Connect your GitHub repository to Render.
2. Select **Web Service** with the following settings:
   - **Environment:** `Python 3`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Configure Environment Variables:
   ```env
   APP_ENV=production
   APP_DEBUG=false
   SECRET_KEY=[GENERATE_64_CHAR_HEX_KEY]
   TOKEN_ENCRYPTION_KEY=[GENERATE_32_CHAR_HEX_KEY]
   DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PWD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   DATABASE_URL_SYNC=postgresql://postgres.[REF]:[PWD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require
   ALLOWED_ORIGINS=["https://[YOUR-VERCEL-FRONTEND].vercel.app"]
   FRONTEND_URL=https://[YOUR-VERCEL-FRONTEND].vercel.app
   SUPABASE_URL=https://[PROJECT-REF].supabase.co
   SUPABASE_ANON_KEY=[YOUR_ANON_KEY]
   SUPABASE_SERVICE_ROLE_KEY=[YOUR_SERVICE_KEY]
   SUPABASE_JWT_SECRET=[YOUR_JWT_SECRET]
   GEMINI_API_KEY=[YOUR_GEMINI_KEY]
   MAX_MONTHLY_SPEND_USD=0.00
   MAX_DAILY_SPEND_USD=0.00
   ```
4. Verify backend health once deployed:
   ```
   GET https://[YOUR-BACKEND-DOMAIN]/api/v1/health
   # Returns 200 OK with all 9 subsystems healthy
   ```

---

## 5. Background Worker Daemon Deployment

The worker consumes background tasks (video rendering, topic research, QA evaluation, YouTube upload):

### Option A: Cloud Background Worker (Render / Railway)
- **Start Command:** `python -m app.workers.runner`
- Uses the same environment variables as the backend.

### Option B: Local / Self-Hosted Persistent Worker
- Execute on a persistent local server:
  ```powershell
  .\scripts\start-worker.ps1
  ```
- The worker claims jobs using PostgreSQL `FOR UPDATE SKIP LOCKED` without double-processing.

---

## 6. Frontend Deployment (Vercel)

1. Connect the GitHub repository to [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Framework Preset: **Next.js**.
4. Configure Build & Development Settings:
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
5. Configure Environment Variables:
   ```env
   NEXT_PUBLIC_API_URL=https://[YOUR-BACKEND-DOMAIN]
   NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-REF].supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=[YOUR_ANON_KEY]
   ```
6. Click **Deploy**. Vercel will build and assign an HTTPS URL.

---

## 7. Verification & Post-Deployment Smoke Test

1. Navigate to `https://[YOUR-VERCEL-FRONTEND].vercel.app/login`.
2. Register a new account or log in.
3. Visit `/settings/health` to confirm:
   - Backend API connection: **ONLINE**
   - Database connection: **CONNECTED**
   - Queue engine: **OPERATIONAL**
   - AI Provider (Gemini): **ACTIVE (Free Tier)**
   - YouTube publisher: **READY**
4. Perform a sample workflow:
   - Navigate to `/topics` -> Generate topic recommendations.
   - Navigate to `/script-studio` -> Generate script draft.
   - Navigate to `/thumbnail-studio` -> Compose and select thumbnail.
   - Navigate to `/production` -> Run autonomous QA evaluation.
