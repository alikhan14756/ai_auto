# Creator Studio AI — Zero-Cost Staging Deployment Readiness Plan

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Target Environment:** Zero-Cost Staging Topology  
**Date:** 2026-11-08  
**Release Status:** `READY FOR STAGING`

---

## 1. Executive Mission & Scope

This readiness plan establishes the technical and operational blueprint for deploying **Creator Studio AI** to a verified staging environment with a strict **$0.00/month hosting budget**.

In accordance with owner directives:
1. **Frontend Hosting:** GitHub Pages (Next.js Static HTML Export).
2. **Relational Database:** Supabase Free Tier (PostgreSQL 16).
3. **Backend API:** Local-first FastAPI service running on the owner's Windows workstation.
4. **Queue Workers:** Persistent local background worker daemon polling Supabase PostgreSQL via `FOR UPDATE SKIP LOCKED`.
5. **Domain:** Deferred (using GitHub Pages default subdomain and local endpoints).
6. **Hosting Budget:** Strictly $0.00 / month (no paid cloud infrastructure, no cloud VPS fees, zero billable API calls).

---

## 2. Phase Zero — Actual Repository & Architecture Inspection

An empirical inspection of the workspace was conducted on 2026-11-08:

| Subsystem / Component | Current State | Staging Requirement | Discrepancies / Actions |
| :--- | :--- | :--- | :--- |
| **Git Remote** | None configured (`git remote -v` is empty). Local branch: `master`. | GitHub remote repository repository URL. | Owner must create GitHub repository and add remote. |
| **Frontend Directory** | `frontend/` (Next.js 15.1.0, React 19.0.0, TypeScript 5.6.3, Tailwind CSS). | Static HTML export deployed to GitHub Pages. | Parameterize `basePath`, disable image optimization server, enable `output: "export"`. |
| **Frontend Routes** | 25 client pages in `frontend/src/app` (all `"use client"`). Zero dynamic bracket folders (`[id]`). Zero server actions. Zero Next.js API routes (`route.ts`). Zero Next.js middleware. | Static export compatible. | 100% compatible with static export out of the box. |
| **Frontend API Calls** | 5 pages call relative paths (`/api/v1/...`, `/health`), while `lib/auth.ts` uses `BACKEND_URL`. | Configurable base URL via `NEXT_PUBLIC_API_BASE_URL`. | Centralize API URL resolution in `frontend/src/lib/api.ts` to support local and tunnel endpoints. |
| **Backend Directory** | `backend/` (FastAPI 0.115, Python 3.12, Uvicorn 0.32, SQLAlchemy 2.0). | Local-first daemon on Windows. | Provide automated PowerShell startup/stop scripts (`start-staging-backend.ps1`). |
| **Database Migrations** | 10 Alembic migrations (`0001` through `0010`) managing 52 application tables + 1 `alembic_version` table. | Applied cleanly to Supabase PostgreSQL over SSL. | Verify asyncpg and psycopg2 SSL connections with Supabase direct/session pooler. |
| **Authentication** | Supabase Auth JS SDK (`@supabase/supabase-js`) on frontend; JWT HS256 validation (`verify_supabase_jwt`) on backend. | Synchronized Supabase project credentials. | Configure `SUPABASE_JWT_SECRET`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. |
| **Background Workers** | `app.workers.runner` daemon claiming jobs with PostgreSQL `FOR UPDATE SKIP LOCKED`. | Persistent local daemon independent of frontend. | Provide automated PowerShell startup/stop scripts (`start-staging-worker.ps1`). |
| **GitHub Actions** | `.github/workflows/ci.yml` (CI test runner). | Dedicated GitHub Pages deployment workflow. | Create `.github/workflows/deploy-pages.yml` using `actions/deploy-pages@v4`. |
| **Test Baseline** | 239/239 pytest tests passing; 0 TS errors; 0 ESLint warnings. | Regression integrity preserved. | Retain 100% pass rate. |

---

## 3. Required Modifications & Technical Strategy

```mermaid
flowchart TD
    subgraph Browser["User Browser / Client"]
        GHP["GitHub Pages\n(Static HTML/CSS/JS Assets)\nhttps://<owner>.github.io/<repo>/"]
    end

    subgraph Workstation["Owner Local Workstation (Windows)"]
        API["FastAPI Backend Daemon\nhttp://localhost:8000\n(Optional Secure Tunnel for GHP)"]
        WRK["Persistent Background Worker\napp.workers.runner\nLease Heartbeats & Watchdog"]
        LOC_STORAGE["Local Storage Directory\nstorage/staging\n(Rendered Videos, Audio, Thumbs)"]
        FFMPEG["FFmpeg & FFprobe Engine\nLocal Video Compositing"]
    end

    subgraph SupabaseCloud["Supabase Free Cloud Infrastructure"]
        S_DB["Supabase PostgreSQL 16\n52 Application Tables\nDurable Queue (SKIP LOCKED)"]
        S_AUTH["Supabase Auth Engine\nJWT Issuer & User Identity"]
    end

    GHP -->|"Direct HTTPS / Tunnel API Calls"| API
    GHP -->|"User Login / Token Refresh"| S_AUTH
    API -->|"JWT HS256 Verification"| S_AUTH
    API -->|"Asyncpg SSL (Port 5432/6543)"| S_DB
    WRK -->|"Atomic Queue Claim (SKIP LOCKED)"| S_DB
    WRK -->|"Media Assembly & Renders"| FFMPEG
    WRK -->|"Read / Write Assets"| LOC_STORAGE
    API -->|"Serve Static Media"| LOC_STORAGE
```

### Modification 1: Frontend Static Export & API Centralization
- **Next.js Static Export:** Update `frontend/next.config.ts` to support `output: "export"`, `images: { unoptimized: true }`, `trailingSlash: true`, and dynamic `basePath: process.env.NEXT_PUBLIC_BASE_PATH || ""`.
- **API Base URL Parameterization:** Create `frontend/src/lib/api.ts` exporting `getApiUrl(path)` which prefixes `NEXT_PUBLIC_API_BASE_URL || NEXT_PUBLIC_API_URL || "http://localhost:8000"`.
- **Update Fetch Call Sites:** Replace relative `/api/v1/...` and `/health` calls in `analytics`, `automation`, `calendar`, `settings`, and `health` pages with `getApiUrl(...)`.

### Modification 2: Supabase Staging Database Configuration
- Configure connection strings with SSL mode:
  - Asyncpg: `postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?ssl=require`
  - Sync (Alembic): `postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require`
- Document transaction pooler (port 6543) vs session pooler (port 5432) nuances with prepared statements in asyncpg.

### Modification 3: Windows Local Staging Automation
- Create `scripts/start-staging-backend.ps1`:
  - Validates Python virtual environment.
  - Verifies `.env` presence without logging secrets.
  - Checks database connection to Supabase.
  - Runs Alembic migrations (`alembic upgrade head`).
  - Launches Uvicorn on `http://127.0.0.1:8000`.
- Create `scripts/stop-staging-backend.ps1`: Gracefully terminates the backend Uvicorn process.
- Create `scripts/start-staging-worker.ps1`: Launches persistent worker daemon with logging to `storage/logs/staging-worker.log`.
- Create `scripts/stop-staging-worker.ps1`: Gracefully signals the worker daemon to terminate after finishing active job leases.

### Modification 4: GitHub Pages Automated Deployment Workflow
- Create `.github/workflows/deploy-pages.yml`:
  - Triggers on push to `main` / `master` when frontend files change or manual dispatch.
  - Builds Next.js static export using `npm run build`.
  - Sets `NEXT_PUBLIC_BASE_PATH` to `/${{ github.event.repository.name }}`.
  - Uses least-privilege permissions: `pages: write`, `id-token: write`, `contents: read`.
  - Deploys static bundle via `actions/upload-pages-artifact@v3` and `actions/deploy-pages@v4`.

---

## 4. Missing Information & Required Owner Actions

To execute staging deployment, the owner must provide/perform:

1. **GitHub Repository Creation:**
   - Create a GitHub repository (e.g. `creator-studio-ai`).
   - Add remote: `git remote add origin https://github.com/<username>/<repo>.git`.
   - Enable GitHub Pages in repository settings (**Settings -> Pages -> Build and deployment -> Source: GitHub Actions**).
2. **Supabase Free Project Creation:**
   - Create a free project on [database.new](https://database.new).
   - Retrieve database connection string (Session Pooler or Direct on port 5432).
   - Retrieve `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_JWT_SECRET` (from **Project Settings -> API**).
3. **Environment Configuration:**
   - Copy `.env.example` to `.env` and fill in the Supabase values.
   - Maintain `MAX_MONTHLY_SPEND_USD=0.00` (governor locked).

---

## 5. Execution Roadmap

| Step | Phase | Task Description | Verification Artifact |
| :---: | :--- | :--- | :--- |
| **1** | Phase 0 | Repository inspection & readiness plan | `docs/DEPLOYMENT-READINESS-PLAN.md` |
| **2** | Phase 1 | Frontend static export compatibility & GitHub Pages setup | `frontend/next.config.ts`, `docs/GITHUB-PAGES-DEPLOYMENT.md`, `.github/workflows/deploy-pages.yml` |
| **3** | Phase 2 | Supabase database integration & migrations specification | `docs/SUPABASE-STAGING-SETUP.md`, `backend/app/core/config.py` |
| **4** | Phase 3 | Local-first FastAPI backend scripts & CORS hardening | `scripts/start-staging-backend.ps1`, `scripts/stop-staging-backend.ps1` |
| **5** | Phase 4 | Persistent local worker scripts & queue isolation | `scripts/start-staging-worker.ps1`, `scripts/stop-staging-worker.ps1` |
| **6** | Phase 5 | Frontend-to-Backend connection & API centralization | `frontend/src/lib/api.ts`, updated page fetchers, tunnel guidelines |
| **7** | Phase 6 | Staging media storage governance & path traversal protection | `docs/LOCAL-STAGING-OPERATIONS.md`, staging storage directory setup |
| **8** | Phase 7 | AI & provider zero-spend enforcement | Audit verification in `docs/STAGING-LIMITATIONS.md` |
| **9** | Phase 8 | FFmpeg single-concurrency resource management | Worker render handler concurrency limit verified |
| **10** | Phase 9 | Free hosting cloud research (Cloud Run, Render, Fly.io) | `docs/FREE-HOSTING-COMPARISON.md` |
| **11** | Phase 10 | Comprehensive test suite & static build verification | `scripts/test.ps1`, `docs/STAGING-TEST-REPORT.md` |
| **12** | Handover | Final staging documentation, runbooks, and handover | `docs/FINAL-STAGING-HANDOVER.md`, `docs/RELEASE-CHECKLIST.md` |
