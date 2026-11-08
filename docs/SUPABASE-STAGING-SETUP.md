# Creator Studio AI — Supabase Free PostgreSQL Staging Setup Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Database Infrastructure:** Supabase Free Tier (Managed PostgreSQL 16)  
**Hosting Cost:** $0.00 / month  
**Status:** Architecture Validated  

---

## 1. Supabase Free Plan Specifications & Reality Check

Creator Studio AI is fully architected to operate on the **Supabase Free Tier**. However, production stability requires understanding its hard limits:

| Resource Dimension | Supabase Free Allowance | Creator Studio AI Impact & Mitigation |
| :--- | :--- | :--- |
| **Database Storage** | **500 MB** total PostgreSQL disk space | Staging metadata for ~50,000 video projects. Video/audio binaries are stored on local workstation (`storage/`) or Cloudflare R2, **never** in PostgreSQL. |
| **Inactivity Pausing** | Pauses after **7 consecutive days** of zero API/database requests | A paused project returns HTTP 503 until manually unpaused via the Supabase dashboard. Heartbeats from our local worker daemon during active testing keep it awake. |
| **Connection Pooling** | Max **15 direct connections**; PgBouncer pooler available | Backend async SQLAlchemy pool configured to `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=5` to prevent exhausting Supabase connection slots. |
| **Project Quota** | Max **2 active free projects** per Supabase account | Dedicate 1 project exclusively to Creator Studio AI staging. |
| **Egress Bandwidth** | **2 GB / month** egress | API responses transmit structured JSON only; large video media does not traverse Supabase egress. |

> [!WARNING]
> **Never store media binaries or heavy video assets directly in Supabase PostgreSQL or Supabase Storage.**  
> Supabase Storage on the free tier is capped at 1 GB total. Rendered video files (100MB–500MB each) would exhaust the quota within 2–5 renders. Use local staging disk storage (`./storage`) or Cloudflare R2 for all media assets.

---

## 2. Supabase Connection Topologies & SSL Requirements

Supabase provides three distinct connection endpoints. Configure them according to the role:

```mermaid
flowchart TD
    subgraph FastAPI["FastAPI Backend (Async SQLAlchemy / asyncpg)"]
        APP_ASYNC["App Runtime Queries\n(Port 5432 Session Pooler or Direct)"]
    end

    subgraph Migrations["Alembic Migrations (Sync SQLAlchemy / psycopg2)"]
        ALEMBIC_SYNC["Schema Migrations\n(Port 5432 Session Pooler or Direct)"]
    end

    subgraph Workers["Background Queue Worker (asyncpg)"]
        WORKER_ASYNC["Queue Claim (SKIP LOCKED)\n(Port 5432 Session Pooler or Direct)"]
    end

    subgraph Supabase["Supabase Cloud Infrastructure"]
        DIRECT["Direct PostgreSQL (Port 5432)\ndb.<project-ref>.supabase.co"]
        S_POOL["Session Pooler (Port 5432)\naws-0-<region>.pooler.supabase.com"]
        T_POOL["Transaction Pooler (Port 6543)\naws-0-<region>.pooler.supabase.com\n(PgBouncer - Disables Prepared Statements)"]
    end

    APP_ASYNC -->|"DATABASE_URL (Port 5432)"| S_POOL
    ALEMBIC_SYNC -->|"DATABASE_URL_SYNC (Port 5432)"| DIRECT
    WORKER_ASYNC -->|"DATABASE_URL (Port 5432)"| S_POOL
```

### Recommended Configuration
- **Async Runtime (`DATABASE_URL`):**
  ```bash
  DATABASE_URL="postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?ssl=require"
  ```
  *Port 5432 (Session mode) preserves prepared statement caching and standard PostgreSQL connection behavior.*

- **Sync Migrations (`DATABASE_URL_SYNC`):**
  ```bash
  DATABASE_URL_SYNC="postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require"
  ```
  *Used by Alembic runner in `alembic/env.py` with `NullPool`.*

### Transaction Pooler (Port 6543) Protection
If you opt to use the transaction pooler on Port 6543, asyncpg prepared statements will fail with `InvalidPreparedStatementError` unless caching is disabled. Creator Studio AI automatically detects Port 6543 or `pooler.supabase.com` in `backend/app/db/session.py` and injects:
```python
connect_args["prepared_statement_cache_size"] = 0
connect_args["statement_cache_size"] = 0
```

---

## 3. Database Schema & Migration Execution

The application contains **10 Alembic migrations** that define the authoritative **52 application tables**:

```bash
# Verify current migration status
alembic current

# Apply all migrations to Supabase head
alembic upgrade head
```

### Table Clusters Applied:
1. `users`, `channels`, `channel_settings`, `audit_logs`
2. `topics`, `research_sources`
3. `video_projects`, `scripts`, `scenes`, `script_claims`
4. `voice_profiles`, `voiceovers`, `narration_tracks`, `media_assets`, `storyboards`, `video_timelines`, `timeline_scenes`, `caption_assets`, `render_jobs`
5. `thumbnail_compositions`, `youtube_metadata`
6. `qa_reports`, `qa_findings`
7. `youtube_channels`, `resumable_sessions`, `publishing_jobs`
8. `channel_daily_snapshots`, `video_performance_snapshots`, `retention_curves`, `topic_retention_weights`, `performance_recommendations`, `analytics_sync_audits`
9. `workflows`, `workflow_stages`, `workflow_checkpoints`, `automation_policies`, `production_calendars`
10. `jobs` (Durable queue with `FOR UPDATE SKIP LOCKED`)

### Worker Queue Locking on PostgreSQL:
The queue engine in [`backend/app/services/job_queue.py`](file:///d:/auto/ai%20automation/backend/app/services/job_queue.py) executes:
```python
bind = self.db.get_bind()
if bind and bind.dialect.name == "postgresql":
    stmt = stmt.with_for_update(skip_locked=True)
```
This guarantees non-blocking atomic job claims across concurrent worker processes on Supabase PostgreSQL.

---

## 4. Supabase Authentication & JWT Integration

Creator Studio AI pairs the Supabase Auth frontend SDK with backend cryptographic JWT verification:

```
[User Browser]
      | (1) Login via email/password or OAuth
      v
[Supabase Auth Service]
      | (2) Issues JWT signed with Project JWT Secret (HS256)
      v
[User Browser]
      | (3) Passes Bearer Token in Authorization header
      v
[FastAPI Backend (verify_supabase_jwt)]
      | (4) Validates signature against SUPABASE_JWT_SECRET
      | (5) Extracts 'sub' (Supabase User ID) & 'email'
      | (6) Queries or auto-provisions local User record in 'users' table
      v
[Authenticated Endpoint Execution]
```

### Environment Variable Requirements:
- `SUPABASE_URL`: `https://[PROJECT-REF].supabase.co`
- `SUPABASE_ANON_KEY`: `eyJhbGciOi...` (public anonymous key)
- `SUPABASE_JWT_SECRET`: `super-secret-jwt-token-from-supabase-dashboard` (backend only!)
- `SUPABASE_SERVICE_ROLE_KEY`: `eyJhbGciOi...` (backend only, used for administrative provisioning if needed)

---

## 5. Owner Step-by-Step Staging Setup Instructions

1. **Create Supabase Staging Project:**
   - Log in to [supabase.com](https://supabase.com).
   - Click **New Project**, name it `creator-studio-ai-staging`, and set a strong database password.
   - Choose a region geographically close to your location (e.g. `us-east-1` or `eu-central-1`).
2. **Retrieve Connection Strings:**
   - Navigate to **Project Settings** -> **Database** -> **Connection string**.
   - Under **URI**, select **Session mode (Port 5432)**. Copy the connection URI.
   - Replace `[YOUR-PASSWORD]` with the password set in Step 1.
3. **Retrieve Supabase API & Auth Keys:**
   - Navigate to **Project Settings** -> **API**.
   - Copy **Project URL** -> `SUPABASE_URL`
   - Copy **anon public** -> `SUPABASE_ANON_KEY`
   - Copy **service_role secret** -> `SUPABASE_SERVICE_ROLE_KEY`
   - Copy **JWT Secret** -> `SUPABASE_JWT_SECRET`
4. **Update `.env` on Local Workstation:**
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?ssl=require"
   DATABASE_URL_SYNC="postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require"
   SUPABASE_URL="https://[REF].supabase.co"
   SUPABASE_ANON_KEY="[ANON-KEY]"
   SUPABASE_JWT_SECRET="[JWT-SECRET]"
   ```
5. **Apply Database Migrations:**
   ```powershell
   cd backend
   .\.venv\Scripts\activate
   alembic upgrade head
   ```
   *Expected output: All migrations 0001 through 0010 apply successfully.*
