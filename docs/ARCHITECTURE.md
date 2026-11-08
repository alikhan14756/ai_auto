# Creator Studio AI — System Architecture & Topology

**Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Repository:** [github.com/alikhan14756/ai_auto](https://github.com/alikhan14756/ai_auto)  
**System Status:** M01–M15 Full-Lifecycle Production Architecture  

---

## 1. Executive Architecture Summary

Creator Studio AI is an autonomous, full-lifecycle faceless YouTube content production engine. It coordinates automated topic research, script generation with deterministic citation fact-checking, neural voice synthesis, visual storyboard generation, multi-track FFmpeg video compilation, Pillow procedural thumbnail composition, YouTube SEO metadata chaptering, a 14-Point Pre-Publish QA Veto Gate, YouTube OAuth 2.0 resumable publishing, and audience analytics telemetry with an algorithmic feedback loop.

The entire architecture is designed with a strict **$0.00/month operational budget governor**, using official free-tier APIs and local-first execution.

```
+---------------------------------------------------------------------------------------------------+
|                                  CREATOR STUDIO AI MONOREPO                                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  FRONTEND (Next.js 15.1.0, React 19, TypeScript 5.6.3, Tailwind CSS)                              |
|  - Obsidian Dark (#090A0D) + Vivid Ember (#FF7A00) Design System                                  |
|  - 28 Client Studio Pages (Dashboard, Topics, Script, Voice, Visual, Video, QA, Publishing, etc.)    |
|  - Centralized API Client (src/lib/api.ts) with Bearer token injection & graceful offline fallback|
|                                         |                                                         |
|                                         v (REST API HTTP / JSON)                                  |
|                                                                                                   |
|  BACKEND (FastAPI 0.115, Python 3.12, Uvicorn, SQLAlchemy 2.0 Async, Pydantic v2)                 |
|  - 23 Modular REST Routers (/api/v1/*) with RBAC, tenant isolation & exception handlers           |
|  - Hard $0.00 Budget Governor intercepting all billable external provider requests                |
|  - AES-256-GCM Token Encryption for OAuth and API credentials                                    |
|                                         |                                                         |
|                    +--------------------+--------------------+                                    |
|                    |                                         |                                    |
|                    v (Async PostgreSQL / asyncpg)            v (In-Process / Subprocess)          |
|                                                                                                   |
|  DATABASE (Supabase / PostgreSQL 15)                SERVICES & WORKERS (app/workers)              |
|  - 52 Application Tables (Alembic 0001-0010)        - Autonomous Durable Queue Runner             |
|  - Atomic Queue (SELECT ... FOR UPDATE SKIP LOCKED) - Edge-TTS Neural Voice Synthesizer           |
|  - RPO: 0.015s, RTO: 2.54ms verified                - FFmpeg Video & Filtergraph Engine           |
|                                                     - PIL Procedural Thumbnail Compositor         |
|                                                     - YouTube Resumable Upload Client             |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Monorepo Structural Breakdown

| Directory | Subsystems | Technologies & Responsibilities |
| :--- | :--- | :--- |
| `frontend/` | UI Kit, Navigation, Studio Views | Next.js 15.1.0 App Router, React 19, Lucide Icons, Tailwind CSS. Exports static bundle via `output: "export"`. |
| `frontend/src/app/` | 28 Routed Pages | Topics, Scripts, Voice, Visual, Video Editor, SEO, Thumbnails, QA Production, Publishing, Analytics, Calendar, Workflows, Settings. |
| `frontend/src/lib/` | Infrastructure SDKs | `api.ts` (centralized client), `auth.ts`, `supabase.ts`, `types.ts`. |
| `backend/app/api/v1/` | 23 REST Endpoints | FastAPI sub-routers (`topics`, `scripts`, `voice`, `visual`, `video`, `thumbnails`, `metadata`, `qa`, `youtube`, `analytics`, `system`). |
| `backend/app/models/` | 52 SQLAlchemy Models | Declarative Base schemas covering users, channels, jobs, topics, scripts, voices, storyboards, assets, video, QA, publishing. |
| `backend/app/providers/`| AI & Media Providers | Google Gemini 1.5 Flash/Pro, Microsoft Edge Neural TTS, Pexels, Pixabay, Local Mock Engine. |
| `backend/app/services/` | 28 Domain Services | Queue leasing, fact-checking, script evaluation, audio mastering, video timeline, thumbnail composition, QA corrections. |
| `backend/app/workers/`  | Durable Queue Workers| Concurrency runner polling `automation_jobs` with `FOR UPDATE SKIP LOCKED`. |
| `scripts/` | Windows PowerShell CLI | Zero-setup automation (`start-backend.ps1`, `start-worker.ps1`, `test.ps1`, `dev.ps1`, `stop-services.ps1`). |
| `storage/` | Staging Media Root | Local directory holding generated audio, downloaded visual assets, rendered MP4 masters, and exported thumbnails. |

---

## 3. Database Architecture (52 Tables)

The database schema is organized into 10 cohesive domain clusters:

1. **Identity & Tenancy:** `users`, `channels`, `channel_members`, `channel_settings`.
2. **Durable Task Queue:** `automation_jobs`, `job_logs`, `job_dependencies`, `job_locks`.
3. **Research & Ideation:** `topics`, `research_sources`, `trend_snapshots`.
4. **Script & Fact-Checking:** `scripts`, `script_sections`, `script_claims`, `script_revisions`.
5. **Neural Voice:** `voice_profiles`, `narration_tracks`, `voiceover_chunks`, `audio_markers`.
6. **Visual Planning & Media:** `storyboards`, `scenes`, `media_assets`, `visual_layers`, `asset_licenses`.
7. **Video Production:** `video_timelines`, `timeline_tracks`, `render_jobs`, `video_master_files`.
8. **Thumbnail & SEO:** `thumbnail_compositions`, `thumbnail_variants`, `metadata_drafts`, `seo_scores`.
9. **Quality Assurance & Governance:** `qa_runs`, `qa_findings`, `qa_exceptions`, `qa_readiness_checks`.
10. **Publishing & Analytics:** `publishing_jobs`, `youtube_videos`, `analytics_snapshots`, `retention_curves`, `workflow_runs`, `workflow_steps`, `workflow_failures`.

---

## 4. Concurrency & Queue Execution Model

The durable worker daemon executes tasks transactionally without external message brokers like Redis:
1. Workers query pending jobs using `SELECT id FROM automation_jobs WHERE status = 'PENDING' ORDER BY priority ASC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1`.
2. PostgreSQL atomically locks the selected row, skipping jobs claimed by other concurrent workers.
3. If a worker process abruptly crashes, the active transaction rolls back automatically, returning the job to `PENDING` state with zero job loss.
4. Leases expire automatically after a configurable heartbeat timeout (default: 300 seconds).

---

## 5. Security & Zero-Cost Spending Governor

- **Spend Governor:** Every provider call passes through `app/services/orchestration/governor.py`. The monthly budget ceiling is hard-locked at `$0.00`. Any paid API call raises `AIBudgetExceededError` before network dispatch.
- **Token Security:** Sensitive credentials (Google OAuth refresh tokens, API keys) are encrypted on disk and in database columns using AES-256-GCM via `app/core/security.py`.
- **CORS & Headers:** FastAPI enforces strict CORS with origin whitelisting, Content Security Policy, and HTTP Bearer token validation with JWT signature verification.
