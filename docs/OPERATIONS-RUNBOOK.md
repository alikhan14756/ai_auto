# Creator Studio AI — Operations and Incident Runbook

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Operations  
**Release Version:** v0.1.0-RELEASE  

---

## 1. Daily Operations & Worker Management

### Starting Services on Windows (Local Development / Staging)

1. **Start Complete Stack:**
   ```powershell
   .\scripts\dev.ps1
   ```
   Lunches Backend API, Worker Daemon, and Frontend Next.js in parallel.

2. **Start Backend API Only:**
   ```powershell
   .\scripts\dev.ps1 -BackendOnly
   ```
   API docs live at `http://localhost:8000/docs`.

3. **Start Background Queue Worker Daemon Only:**
   ```powershell
   .\scripts\worker.ps1
   ```
   Worker polls durable PostgreSQL queue for video pipeline tasks with heartbeats.

4. **Start Frontend Next.js Interface Only:**
   ```powershell
   .\scripts\dev.ps1 -FrontendOnly
   ```
   App accessible at `http://localhost:3000`.

5. **Run Full Master Verification Suite:**
   ```powershell
   .\scripts\test.ps1
   ```

---

## 2. Admin Operational Health Dashboard

Platform operators can monitor live system health at:
- **URL:** `http://localhost:3000/settings/health`
- **Telemetry Monitored:**
  - Database connection driver (`asyncpg`) and latency.
  - Active and queued workflow stages.
  - Stalled stages detected by the 180s watchdog.
  - Spend governor compliance ($0.00 ceiling).
  - YouTube OAuth integration status and token encryption state.
  - Incident & diagnostic log table with suggested resolutions.

---

## 3. Common Operational Incidents & Triage

### Incident A: Worker Crashes or Jobs Stuck in `PROCESSING`
- **Symptom:** Job status remains `PROCESSING` with no heartbeat updates for $> 180$ seconds.
- **Automated Watchdog Action:** The background watchdog (`ProductionHealthMonitor`) detects expired leases and reclaims the job automatically, scheduling an exponential backoff retry (up to 3 times).
- **Manual Resolution:**
  ```bash
  # Check active worker status
  curl -X GET http://localhost:8000/api/v1/system/production-health
  # Restart worker daemon
  .\scripts\worker.ps1
  ```

### Incident B: Gemini API Rate Limit (HTTP 429)
- **Symptom:** `AIRateLimitError: Gemini Free Tier RPM limit (15 req/min) exceeded`.
- **Resolution:** The sliding-window rate limiter throttles calls. If external API returns 429, the durable queue retries automatically after $2^{\text{attempt}-1} \times 30\text{s}$.

### Incident C: Budget Circuit Breaker Trip (HTTP 402)
- **Symptom:** `AIBudgetExceededError: Channel monthly spending cap is $0.00`.
- **Resolution:** Navigate to `/settings/usage` to inspect token consumption. If paid inference is explicitly approved by the channel owner, update `max_monthly_spend_usd` in `channel_settings`.

### Incident D: YouTube Upload Interrupted / Resumable Session Stalled
- **Symptom:** Publishing job halts midway through chunk upload.
- **Resolution:**
  1. The M12 resumable protocol queries the upload URI with `Content-Range: bytes */total_bytes` to retrieve the last received byte index.
  2. The worker automatically resumes streaming from that offset without restarting the upload from byte 0.
  3. If OAuth token expired, the backend automatically exchanges the AES-256-GCM encrypted refresh token for a new access token.

### Incident E: M11 QA Veto Gate Blocks Video Publication
- **Symptom:** Publishing is rejected with message: `Publication vetoed by M11 QA Gate: Score X/100`.
- **Policy Enforcement:**
  - Under no circumstances should the QA gate be bypassed or disabled.
  - Inspect the specific failure in `/publication` or `/api/v1/system/failures`:
    - If unverified factual claims exist: verify claims in Script Studio or edit claims.
    - If audio loudness exceeds $-1.0$ dBTP: re-render audio track with true peak limiter.
    - If freeze/black frame exceeds thresholds: inspect FFmpeg storyboard visual assets.
  - Once corrected, run a new QA evaluation. When the overall score $\ge 70.0$ and verdict is `APPROVED`, publication unlocks automatically.

---

## 4. Configuring Real External Providers

### Google Gemini API
1. Open `.env` in the root workspace.
2. Set:
   ```env
   GEMINI_API_KEY=your-actual-api-key-here
   ```
3. Restart backend API. Factory automatically switches from `MockAIProvider` to `GeminiProvider`.

### YouTube OAuth 2.0 Credentials
1. In Google Cloud Console, enable YouTube Data API v3 and YouTube Analytics API.
2. Create OAuth 2.0 Client ID (Web Application).
3. Set Authorized Redirect URI: `http://localhost:8000/api/v1/youtube/oauth2callback`.
4. In `.env`:
   ```env
   YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   YOUTUBE_CLIENT_SECRET=your-client-secret
   ```
5. Authorize channel from Settings -> YouTube in the web dashboard.
