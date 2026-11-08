# CREATOR STUDIO AI — WORKER OPERATIONS & QUEUE GUIDE

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**Queue Subsystem:** Durable PostgreSQL Job Queue (`automation_jobs` table)  
**Concurrency Protocol:** `FOR UPDATE SKIP LOCKED`

---

## 1. Queue Architecture & Job Lifecycle

Creator Studio AI eliminates external message broker dependencies (e.g. Redis, RabbitMQ) by leveraging PostgreSQL's transactional durability and `FOR UPDATE SKIP LOCKED` row-level locking.

```
[ Client / API Request ] 
          |
          v
[ JobQueueService.enqueue_job() ]
          |
          v
[ PostgreSQL automation_jobs Table (status: QUEUED) ]
          |
          v
[ Worker Daemon (runner.py) ] ---> FOR UPDATE SKIP LOCKED
          |
          +---> status: RUNNING
          |
          +---> Execute Handler (Video Render, Voice, Topic, QA, Upload)
          |
          +---> Success: status = COMPLETED
          |
          +---> Failure: Retry with Exponential Backoff (attempts < max_retries)
          |
          +---> Exhausted: status = DEAD_LETTER
```

---

## 2. Registered Queue Job Handlers

| Job Type | Handler File | Description | Priority |
| :--- | :--- | :--- | :---: |
| `TOPIC_RESEARCH_PIPELINE` | `app/workers/handlers/topic_research.py` | Topic discovery, velocity calculation, market evaluation | 5 |
| `SCRIPT_GENERATION` | `app/workers/handlers/script_generation.py` | 3-act narrative drafting and claim extraction | 5 |
| `VOICE_SYNTHESIS` | `app/workers/handlers/voice_synthesis.py` | TTS audio narration rendering and LUFS normalization | 6 |
| `STORYBOARD_PLANNING` | `app/workers/handlers/storyboard.py` | Visual shot planning and media asset search | 5 |
| `VIDEO_RENDER` | `app/workers/handlers/video_rendering.py` | Subtitle rendering, audio mixing, FFmpeg assembly | 10 |
| `THUMBNAIL_CONCEPT_GENERATION` | `app/workers/handlers/thumbnail.py` | Layered thumbnail synthesis and contrast validation | 5 |
| `QA_PACKAGE_INSPECTION` | `app/workers/handlers/qa_inspection.py` | 14-point autonomous QA check and veto calculation | 1 |
| `YOUTUBE_PUBLICATION_DISPATCH` | `app/workers/handlers/youtube_publishing.py`| Resumable chunked upload to YouTube Data API | 8 |
| `YOUTUBE_DAILY_ANALYTICS_SYNC` | `app/workers/handlers/analytics.py` | Daily YouTube Analytics v2 data ingestion | 3 |
| `WORKFLOW_STAGE_EXECUTE` | `app/workers/handlers/orchestration.py` | Stage state advancement in multi-step workflows | 7 |

---

## 3. Worker Operations & Control Commands

### 3.1. Starting the Worker Daemon (Windows PowerShell)
```powershell
.\scripts\start-worker.ps1
```
Or directly from the backend virtual environment:
```powershell
cd backend
.venv\Scripts\python -m app.workers.runner
```

### 3.2. Stopping the Worker Daemon
```powershell
.\scripts\stop-staging-worker.ps1
```
The script locates the worker PID in `storage/staging-worker.pid` and gracefully terminates the process.

### 3.3. Checking Worker Health & Logs
Worker activity is recorded in:
- `storage/staging-worker.log`
- Or via the API: `GET /api/v1/jobs/telemetry`

---

## 4. Fault Tolerance, Retries & Dead-Letter Handling

- **Crash Recovery & Watchdog:** If a worker crashes mid-task, the watchdog in `app/services/orchestration/health_monitor.py` detects orphaned jobs in `RUNNING` status whose heartbeat has timed out and re-queues them.
- **Bounded Backoff:** Failed jobs retry with exponential backoff:
  $$\text{delay} = \text{initial\_backoff} \times 2^{\text{retry\_count}}$$
- **Dead-Letter Queue:** When `retry_count >= max_retries` (default: 3), the job transitions to `DEAD_LETTER` status with the complete stack trace preserved in `last_error_message`.
- **Manual Retry API:** Dead-letter jobs can be re-enqueued via `POST /api/v1/jobs/{job_id}/retry`.
