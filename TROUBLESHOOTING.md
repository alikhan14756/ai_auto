# CREATOR STUDIO AI — TROUBLESHOOTING & DIAGNOSTIC RUNBOOK

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**Diagnostics Level:** Production & Staging Operations

---

## 1. Quick Diagnostic Checklist

When encountering an operational issue, execute these checks in order:

1. **Verify Backend Health:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"
   ```
   *Expected:* HTTP 200 with status `"healthy"`.

2. **Verify Database Connectivity:**
   ```powershell
   cd backend
   .venv\Scripts\alembic current
   ```
   *Expected:* Output showing current revision `0010_add_workflow_orchestration_and_policies (head)`.

3. **Verify Worker Heartbeat:**
   Check `storage/staging-worker.log` for active poll loops:
   `[WorkerRunner] Polling for queued jobs...`

4. **Verify Frontend Static Assets:**
   ```powershell
   npm --prefix frontend run build
   ```
   *Expected:* 28/28 pages compiled without errors.

---

## 2. Common Operational Issues & Remediation

### 2.1. Supabase SSL Handshake Failure
- **Symptom:** `asyncpg.exceptions.ConnectionDoesNotExistError` or `SSL connection has been closed unexpectedly`.
- **Root Cause:** Supabase requires SSL encryption for all external connections.
- **Solution:** Ensure `app/db/session.py` contains `connect_args["ssl"] = "require"`. This is automatically injected for hosts containing `supabase.co` or `supabase.com`.
- **Direct Alembic fix:** Ensure `DATABASE_URL_SYNC` includes `?sslmode=require`.

### 2.2. Supabase PgBouncer Prepared Statement Error
- **Symptom:** `asyncpg.exceptions.InvalidSQLStatementNameError: prepared statement "_pg3_..." does not exist`.
- **Root Cause:** Transaction poolers (port 6543) do not support PostgreSQL prepared statement caching across pooled connections.
- **Solution:** Verify `connect_args["statement_cache_size"] = 0` in `app/db/session.py` when port 6543 or `pooler.supabase.com` is used.

### 2.3. Browser Mixed Content & Cross-Origin Blocks
- **Symptom:** Browser console error `Blocked loading mixed active content "http://localhost:8000/..."` when accessing frontend via HTTPS (e.g. GitHub Pages or Vercel).
- **Root Cause:** Modern browsers block insecure HTTP API calls from HTTPS pages.
- **Solution:**
  - For local staging: Access both frontend and backend over HTTP (`http://localhost:3000` -> `http://localhost:8000`).
  - For cloud production: Host backend on an HTTPS-enabled domain (Render, Railway, Fly.io) and set `NEXT_PUBLIC_API_URL=https://[YOUR-BACKEND-DOMAIN]`.

### 2.4. CORS Policy Origin Rejection
- **Symptom:** `Access to fetch at '...' from origin '...' has been blocked by CORS policy`.
- **Solution:** Update `ALLOWED_ORIGINS` in `backend/.env` to include the calling frontend origin:
  ```env
  ALLOWED_ORIGINS=["http://localhost:3000","https://[YOUR-APP].vercel.app"]
  ```

### 2.5. YouTube Resumable Upload Veto Gate Block
- **Symptom:** `POST /api/v1/youtube/publish` returns `400 Bad Request` with detail `ERR_QA_VETO_BLOCKED`.
- **Root Cause:** Non-bypassable M11 QA Veto Gate detected that no passing QA evaluation exists for the video package.
- **Solution:**
  1. Navigate to `/production` and trigger an automated QA run (`handleRerunQA`).
  2. Resolve any `CRITICAL` or `HIGH` findings.
  3. Alternatively, an administrator can authorize an override via `POST /api/v1/qa/exceptions`.

### 2.6. Gemini AI Provider Quota Exhaustion
- **Symptom:** `402 Payment Required` or `429 Too Many Requests` during topic research or script generation.
- **Root Cause:** Gemini free tier limit reached (15 RPM or 1,500 RPD) or Spend Governor prevented non-zero spend.
- **Solution:**
  - The system automatically engages exponential backoff with jitter.
  - In staging/development, mock fallback providers can be enabled via `APP_ENV=development` to simulate full responses with zero API consumption.

### 2.7. FFmpeg Binary Not Found
- **Symptom:** Video rendering job fails with `FFmpeg executable not found in PATH`.
- **Solution:**
  - Install FFmpeg and add it to the system `PATH`.
  - Alternatively, set `VIDEO_RENDERER_DEFAULT_MODE=mock` in `backend/.env` for local testing without FFmpeg installed.
