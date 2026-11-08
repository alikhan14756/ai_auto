# Creator Studio AI — Staging Operations Runbook

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Document Status:** Site Reliability & Operational Procedures  
**Date:** 2026-11-08  

---

## 1. Daily Operations & Routine Maintenance

### 1.1 Service Status Check
To verify all staging services are operating nominally:
```bash
# Container state
docker compose ps

# Backend health probe
curl -s http://localhost:8000/api/v1/health | jq .

# Watchdog & stalled workflow telemetry
curl -s http://localhost:8000/api/v1/system/production-health | jq .
```

### 1.2 Queue & Worker Inspection
To inspect active, queued, or retrying jobs in the database:
```bash
docker compose exec postgres psql -U postgres -d creator_studio_ai -c "
  SELECT id, job_type, status, current_stage, retry_count, created_at 
  FROM automation_jobs 
  WHERE status IN ('QUEUED', 'RUNNING', 'RETRYING') 
  ORDER BY created_at DESC 
  LIMIT 10;
"
```

---

## 2. Incident Triage & Recovery Playbooks

### Playbook 1: Stalled Workflow or Dead Worker Process
- **Symptom:** A video production job remains in `RUNNING` state beyond 180 seconds without progress updates.
- **Root Cause:** Worker process crashed, ran out of memory during rendering, or was terminated by OS OOM killer.
- **Automated Remedy:** The built-in watchdog daemon will automatically detect the lease expiration (lease > 120s) and reclaim the job on the next tick, re-queuing it if `retry_count < max_retries`.
- **Manual Intervention (If Watchdog is Paused):**
```bash
# Restart worker container
docker compose restart worker

# Check worker logs
docker compose logs -f --tail=100 worker
```

### Playbook 2: YouTube API Quota Exhaustion (`quotaExceeded`)
- **Symptom:** Publishing job fails with error message: `Google API Error: 403 quotaExceeded`.
- **Cause:** Daily YouTube Data API v3 quota limit (10,000 units/day) has been consumed (typically after 5–6 video uploads).
- **Remedy:**
  1. The durable queue marks the job as `PUBLISHING_FAILED_RETRYABLE`.
  2. The next retry is automatically scheduled for `00:00 PST` (Pacific Standard Time) when Google resets quotas.
  3. No manual database edits are required. Do not repeatedly retry jobs manually, as this will consume further quota units on read calls.

### Playbook 3: Google Gemini Rate Limit (`429 RESOURCE_EXHAUSTED`)
- **Symptom:** Topic discovery or script generation job reports `AIRateLimitError`.
- **Cause:** Free tier sliding-window limit (15 requests/minute) exceeded due to burst requests.
- **Remedy:** The `GeminiRateLimiter` pauses outbound calls automatically. If bursts persist, verify that worker concurrency is limited to 1 worker per free API key.

---

## 3. Secret Rotation Procedures

### 3.1 Google Gemini / YouTube OAuth Key Rotation
1. Generate new API credentials in Google Cloud Console.
2. Update `.env` with the new values:
   - `GEMINI_API_KEY=new_key`
   - `YOUTUBE_CLIENT_SECRET=new_secret`
3. Restart backend API and worker:
   ```bash
   docker compose up -d api worker
   ```
4. Verify `/settings/health` reflects the new active provider.

### 3.2 Master Application Encryption Key Rotation (`APP_MASTER_ENCRYPTION_KEY`)
> [!CAUTION]
> The master encryption key encrypts all channel OAuth refresh tokens stored in the `channels` table. If this key is replaced without re-encrypting existing tokens, existing channels will fail decryption.

**Procedure for Re-Encrypting Stored Tokens:**
1. Generate new 32-byte key: `NEW_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")`
2. Run database migration script using both old and new keys to decrypt and re-encrypt tokens.
3. Update `APP_MASTER_ENCRYPTION_KEY` in `.env` to `$NEW_KEY`.
4. Restart services.
