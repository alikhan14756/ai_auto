# Complete Development Roadmap & Implementation Plan
## Creator Studio AI — 15-Milestone Production Blueprint

**Document Version:** 1.0.0  
**Status:** Approved for Implementation Execution  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  

---

### Table of Contents
1. [Implementation Strategy & Phase Gate Model](#1-implementation-strategy--phase-gate-model)
2. [Milestone 01: Repository Setup, Architecture Foundation & Dev Environment](#milestone-01-repository-setup-architecture-foundation--dev-environment)
3. [Milestone 02: Frontend Dashboard, Design System & Navigation](#milestone-02-frontend-dashboard-design-system--navigation)
4. [Milestone 03: Database Schema, Supabase Auth & Backend REST API](#milestone-03-database-schema-supabase-auth--backend-rest-api)
5. [Milestone 04: Durable Job Queue & Worker Daemon Engine](#milestone-04-durable-job-queue--worker-daemon-engine)
6. [Milestone 05: Gemini AI Provider & Topic Research Engine](#milestone-05-gemini-ai-provider--topic-research-engine)
7. [Milestone 06: Script Generation & Factual Verification Studio](#milestone-06-script-generation--factual-verification-studio)
8. [Milestone 07: Local Voice Generation & Audio Mastering](#milestone-07-local-voice-generation--audio-mastering)
9. [Milestone 08: Scene Storyboard & Playwright Media Capture](#milestone-08-scene-storyboard--playwright-media-capture)
10. [Milestone 09: FFmpeg Video Rendering & Kinetic Typography Subtitles](#milestone-09-ffmpeg-video-rendering--kinetic-typography-subtitles)
11. [Milestone 10: Thumbnail Composition & YouTube SEO Metadata](#milestone-10-thumbnail-composition--youtube-seo-metadata)
12. [Milestone 11: Deterministic Quality Assurance Veto Gate](#milestone-11-deterministic-quality-assurance-veto-gate)
13. [Milestone 12: YouTube OAuth 2.0 & Resumable Publishing](#milestone-12-youtube-oauth-20--resumable-publishing)
14. [Milestone 13: YouTube Analytics Ingestion & Topic Optimization Loop](#milestone-13-youtube-analytics-ingestion--topic-optimization-loop)
15. [Milestone 14: Security Hardening, Automated Testing & Deployment](#milestone-14-security-hardening-automated-testing--deployment)
16. [Milestone 15: End-to-End Autonomous Pipeline Verification & Launch](#milestone-15-end-to-end-autonomous-pipeline-verification--launch)

---

### 1. Implementation Strategy & Phase Gate Model

The project is structured into **15 sequential, independently verifiable milestones**. 

Following the strict GSD and Ralph Loop engineering discipline:
- **No Mock Stubs:** Features must be backed by working code, schema definitions, and integration tests.
- **Phase Gate Verification:** A milestone is only marked complete once its objective automated tests pass.
- **MVP Priority:** All milestones up to M12 deliver a functional, zero-cost video generation and publishing loop. M13–M15 provide autonomous self-optimization and cloud deployment hardening.

---

### Milestone 01: Repository Setup, Architecture Foundation & Dev Environment
- **Objective:** Establish the dual-monorepo structure (Next.js frontend + FastAPI backend), toolchains, linters, and developer environment on Windows.
- **Features:** Unified workspace scripts, TypeScript strict configuration, Python 3.11 virtual environment, pre-commit hooks.
- **Tasks:**
  1. Initialize git repository with root `.gitignore`.
  2. Setup `frontend/` using Next.js 15 (App Router, Tailwind CSS, Lucide, TypeScript).
  3. Setup `backend/` using Poetry or `requirements.txt` (FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest).
  4. Configure environment file templates (`.env.example`).
  5. Verify local execution of FFmpeg 6.x and Playwright browsers on Windows.
- **Dependencies:** None.
- **Files Expected:** `package.json`, `frontend/package.json`, `backend/pyproject.toml`, `backend/main.py`.
- **Acceptance Criteria:** `npm run dev` serves the Next.js shell; `pytest` runs and passes on empty backend test suite; `ffmpeg -version` and `playwright install` succeed.
- **Tests:** Environment smoke test running FFmpeg check and FastAPI root health endpoint (`GET /health`).
- **Potential Risks:** Windows path delimiter collisions; mitigated by using Python `pathlib.Path` exclusively.
- **Definition of Done:** Both frontend and backend spin up simultaneously with zero console warnings.

---

### Milestone 02: Frontend Dashboard, Design System & Navigation [COMPLETED]
- **Objective:** Build the complete dark-first UI design system, navigation shell, responsive layout, and screen skeletons.
- **Status:** **COMPLETE & VERIFIED (2026-11-07)**
- **Features Delivered:**
  - Obsidian dark-first theme (`#090A0D` canvas, `#FF7A00` Vivid Ember accent).
  - Collapsible desktop sidebar with 4 navigation groups (Workspace, AI Production, Management, System) and tooltips.
  - Responsive mobile drawer navigation with slide-in animation and backdrop.
  - Interactive top header with channel status, 14 QA check badge, notifications dropdown, and search.
  - Complete Reusable Component Library: `Button`, `Card`, `Badge`, `ProgressBar`, `StatCard`, `EmptyState`, `Modal`, `Dropdown`, `Tooltip`, `Table`, `Skeleton`, `PageHeader`, `NotificationBanner`, `Input`.
  - Executive Dashboard with 5 StatCards, pipeline stepper, active jobs table, upcoming schedule, and retention benchmark.
  - Interactive "Create Video" modal dialog supporting Long-Form (16:9) and Shorts (9:16) format selection.
  - All 21 navigation routes scaffolded with structured placeholders and feature lists.
- **Verification & Tests:**
  - `npm run typecheck`: PASSED (0 errors).
  - `npm run lint`: PASSED (0 warnings, 0 errors).
  - `next build`: PASSED (All 25 static pages compiled & optimized).
  - `scripts/test.ps1`: PASSED (100% across backend and frontend).

---

### Milestone 03: Database Schema, Supabase Auth & Backend REST API
- **Objective:** Implement the 21 relational models in PostgreSQL via SQLAlchemy 2.0, run Alembic migrations, and wire Supabase Auth.
- **Features:** User authentication, JWT verification middleware, database connection pooling, CRUD API endpoints.
- **Tasks:**
  1. Configure Supabase PostgreSQL connection pool via asyncpg.
  2. Implement 21 SQLAlchemy models in `backend/app/models/`.
  3. Generate and execute initial Alembic migration (`0001_initial_schema.py`).
  4. Implement `SupabaseJWTBearer` dependency in FastAPI for route protection.
  5. Build CRUD REST routers for Channels, Projects, Topics, and Settings.
- **Dependencies:** Milestone 01, Milestone 02.
- **Files Expected:** `backend/app/models/*.py`, `backend/app/api/v1/*.py`, `backend/alembic/versions/*`.
- **Acceptance Criteria:** API returns HTTP 200/201 with typed JSON; unauthenticated requests receive HTTP 401; DB foreign keys enforce relational integrity.
- **Tests:** Pytest integration tests executing CRUD queries against test PostgreSQL database.
- **Potential Risks:** Schema migration locks; mitigated by testing Alembic downgrade and upgrade scripts.
- **Definition of Done:** Frontend can fetch live channel and project data from backend API with authenticated tokens.

---

### Milestone 04: Durable Job Queue & Worker Daemon Engine [COMPLETED & VERIFIED]
- **Objective:** Create the transactional PostgreSQL background worker system with atomic claiming, heartbeats, and exponential retries.
- **Features:** `FOR UPDATE SKIP LOCKED` task queue, worker heartbeat daemon, crash recovery watchdog, idempotency enforcement.
- **Tasks:**
  1. Implement `JobQueueService` for atomic queue operations.
  2. Create worker execution runner in `backend/app/workers/runner.py`.
  3. Implement heartbeat updater and stale job watchdog (reclaims crashed jobs after 2 minutes).
  4. Implement exponential backoff retry math ($2^n \times 30\text{s}$) with max 3 attempts.
  5. Add Server-Sent Events (SSE) progress streaming endpoint (`/api/v1/projects/{id}/progress-stream`).
- **Dependencies:** Milestone 03.
- **Files Expected:** `backend/app/services/job_queue.py`, `backend/app/workers/*.py`.
- **Acceptance Criteria:** 10 simulated concurrent jobs are claimed by workers without duplicate execution; interrupted workers recover tasks cleanly.
- **Tests:** Concurrency stress test verifying zero race conditions on job claiming.
- **Potential Risks:** Database connection exhaustion; mitigated by connection pooling and strict async session scoping.
- **Definition of Done:** Jobs transition from `QUEUED` -> `PROCESSING` -> `COMPLETED` with real-time UI progress updates.

---

### Milestone 05: Gemini AI Provider & Topic Research Engine [COMPLETED & VERIFIED]
- **Objective:** Implement the AI Provider abstraction layer, Gemini 1.5 Flash/Pro integration, token quota tracking, and RSS topic ingestion.
- **Features:** `AIProviderInterface`, Gemini client with JSON Schema enforcement, token bucket rate limiter, RSS feed parser, Topic Opportunity Scoring.
- **Tasks:**
  1. Build `AIProviderInterface` and `GeminiProvider` implementation.
  2. Implement `UsageTrackingService` with strict free-tier limits (15 RPM / 1,500 RPD) and $0.00 hard budget circuit breaker.
  3. Create `TopicResearchService` pulling Hacker News, Reddit tech, and GitHub trending feeds.
  4. Implement `TopicScoringService` scoring opportunity based on search interest, competition, and channel alignment.
- **Dependencies:** Milestone 04.
- **Files Expected:** `backend/app/providers/ai/*.py`, `backend/app/services/topic_*.py`.
- **Acceptance Criteria:** System generates 10 scored topic blueprints from live web feeds without exceeding Gemini free tier quotas.
- **Tests:** Unit tests mocking Gemini API responses and testing quota limiter edge cases.
- **Potential Risks:** API rate limit (HTTP 429); mitigated by automatic exponential backoff and request throttling.
- **Definition of Done:** Creator can click "Discover Topics" in UI and view scored topics populated in the database.

---

### Milestone 06: Script Generation & Factual Verification Studio [COMPLETED & VERIFIED]
- **Objective:** Procedurally generate structured 5-part video scripts and execute web search claim verification.
- **Features:** Long-form & Shorts prompt templates, Claim Extraction parser, Search API integration, confidence evaluator, scene synchronization, section regeneration, quality metrics.
- **Tasks:**
  1. Implement structured JSON prompts for video scripts with scene breakdown (`ScriptGenerationService`).
  2. Implement claim extraction regex/LLM parser to isolate numbers, benchmarks, and releases into `ScriptClaim` records.
  3. Implement `FactCheckingService` cross-referencing claims against `ResearchSource` records and populating citation URLs and snippets.
  4. Implement `ScriptEvaluationService` computing spoken duration at 140 WPM, hook strength, clarity, repetition index, and composite quality score.
  5. Connect frontend Script Studio (`/script-studio`) and Fact-Checking matrix to live backend data with section regeneration and approval/locking controls.
  6. Register worker queue handlers (`GENERATE_SCRIPT`, `SCRIPT_OUTLINE_GENERATION`, `SCRIPT_FACT_CHECK`, `SCRIPT_QUALITY_EVALUATION`).
- **Dependencies:** Milestone 05.
- **Files Delivered:** `backend/app/schemas/script.py`, `backend/app/services/script_*.py`, `backend/app/services/fact_checking.py`, `backend/app/workers/handlers/script_generation.py`, `backend/app/api/v1/endpoints/scripts.py`, `frontend/src/app/script-studio/page.tsx`.
- **Acceptance Criteria:** Generated script contains zero unverified claims $<0.80$; UI displays color-coded citations and confidence badges; 80/80 backend tests passed; 27/27 frontend pages statically built.
- **Definition of Done:** User can review, edit, regenerate sections, and approve a verified, scene-partitioned script in the Script Studio.

---

### Milestone 07: Local Voice Generation & Audio Mastering [COMPLETED & VERIFIED]
- **Status:** Completed & Verified (98/98 tests passing, 0 TS errors, 0 ESLint warnings, all static routes compiled).
- **Objective:** Synthesize high-quality neural voice narration locally, extract word-level timestamps, and master audio to YouTube broadcast standards.
- **Features:** Local Edge-TTS engine, custom tech pronunciation dictionary, pure-Python RIFF WAV & loudness engine (-14 LUFS), word timestamp aligner, single-scene regeneration, persistent Voice Studio UI.
- **Tasks:**
  1. Implement `VoiceGenerationService` using `edge-tts` (or local Kokoro). [COMPLETED]
  2. Build pronunciation replacement lexicon (SSML mapping for tech terms). [COMPLETED]
  3. Implement pure-Python audio post-processing (WAV parser, dynamic RMS/LUFS estimation, calibrated silence insertion). [COMPLETED]
  4. Extract and parse word-level timestamps into JSON structure `[{ word, start, end }]`. [COMPLETED]
  5. Connect frontend Voice Studio with audio waveform player and chunk inspector. [COMPLETED]
- **Dependencies:** Milestone 06.
- **Files Expected:** `backend/app/services/voice_*.py`, `backend/app/utils/audio.py`.
- **Acceptance Criteria:** Audio output measures $-14.0\text{ LUFS} \pm 1.0\text{ LUFS}$; max true peak $\le -1.0\text{ dBTP}$; word timestamps align with audio track. [VERIFIED]
- **Tests:** Pure-Python RIFF WAV and LUFS analysis test validating loudness and silence thresholds. [VERIFIED: 18 dedicated tests]
- **Potential Risks:** Distorted audio clipping; mitigated by automatic gain adjustment in post-processing.
- **Definition of Done:** Script scenes have mastered WAV audio files and word timestamps rendered to disk and playable in UI. [VERIFIED]

---

### Milestone 08: Visual Planning, Asset Discovery & AI Image Generation [COMPLETED & VERIFIED]
- **Status:** Completed & Verified (116/116 backend tests passing, 0 TypeScript errors, 0 ESLint warnings, 27/27 static routes compiled).
- **Objective:** Convert approved scripts and voiceover timing into a structured visual storyboard and build a searchable media library with external stock discovery and AI image synthesis.
- **Features:** Visual planning engine with purpose and archetype classification, provider-independent stock discovery (Pexels, Pixabay, Mock), AI image generation (Gemini / Mock), licensing provenance engine with `LICENSE_REVIEW_REQUIRED` safeguards, SHA-256 asset hashing, and Obsidian design system Visual Studio & Media Library.
- **Tasks:**
  1. Implement `VisualPlanningService` mapping scripts and narration audio to visual archetypes, search keywords, prompts, and transitions. [COMPLETED]
  2. Implement visual provider layer: `MockStockProvider`, `MockImageProvider`, `PexelsProvider`, `PixabayProvider`, `GeminiImageProvider`. [COMPLETED]
  3. Implement `VisualAssetService` handling stock discovery, image generation, secure upload with magic byte sniffing, and licensing management. [COMPLETED]
  4. Create Alembic migration `0004_add_storyboards_and_media_asset_enhancements.py` for `storyboards`, `scenes`, and `media_assets`. [COMPLETED]
  5. Implement durable worker queue handlers: `STORYBOARD_GENERATION`, `VISUAL_ASSET_SEARCH`, `IMAGE_GENERATION`. [COMPLETED]
  6. Implement REST API endpoints (`/api/v1/visual/*`) and frontend Visual Studio (`/visual-studio`) and Media Library (`/media`). [COMPLETED]
- **Dependencies:** Milestone 07.
- **Acceptance Criteria:** Storyboards generate clean visual manifests; assets are hashed with SHA-256 and categorized; unverified media flagged `LICENSE_REVIEW_REQUIRED`; zero-dollar budget enforced. [VERIFIED: 18 dedicated tests, 116 total]
- **Definition of Done:** Every scene in the project has structured visual specifications, timing alignment, and assigned or discoverable visual assets playable and reviewable in UI. [VERIFIED]

---

### Milestone 09: FFmpeg Video Rendering & Kinetic Typography Subtitles
- **Objective:** Assemble multi-track video, duck background music, generate animated kinetic subtitles, and encode the master 1080p MP4.
- **Features:** Advanced SubStation Alpha (`.ass`) caption compiler, FFmpeg complex filtergraph, background audio ducker, 16:9 and 9:16 layout engines.
- **Tasks:**
  1. Build kinetic ASS subtitle compiler with active-word orange highlighting (`#FF7A00`) and bounce styling.
  2. Construct FFmpeg filtergraph joining scene clips with crossfade transitions.
  3. Implement audio ducking filter lowering background music by 18 dB during speech.
  4. Execute render with progress percentage reporting to database.
  5. Connect video player in `/projects/[id]/preview` to master rendered file.
- **Dependencies:** Milestone 08.
- **Files Expected:** `backend/app/services/video_rendering.py`, `backend/app/utils/subtitles.py`.
- **Acceptance Criteria:** Full 8-minute 1080p MP4 renders in $<12$ minutes on local CPU; captions stay in frame-accurate sync with vocal track.
- **Tests:** FFprobe validation test asserting video codec `h264`, audio codec `aac`, resolution `1920x1080`, and zero stream errors.
- **Potential Risks:** Video out-of-sync with audio; mitigated by aligning scene durations strictly to voiceover audio lengths.
- **Definition of Done:** Complete MP4 video renders to disk and plays smoothly with synced audio and animated captions.

---

### Milestone 10: Thumbnail Composition & YouTube SEO Metadata
- **Objective:** Generate 3 high-contrast graphical thumbnail variants and generate complete YouTube SEO metadata.
- **Features:** Pillow 1280x720 graphic generator (tool logo, bold 3-word title hook, orange glow), title/description/tag generator, synthetic media disclosure tag.
- **Tasks:**
  1. Implement `ThumbnailService` generating 3 layout variants (A/B/C) with dark isometric backgrounds and high-contrast typography.
  2. Implement SEO metadata generator for YouTube titles ($\le 80$ chars), structured markdown descriptions with chapter timestamps, and tags.
  3. Ensure automatic inclusion of the required synthetic media disclosure tag.
  4. Wire Thumbnail Studio UI to allow variant selection and text tweaking.
- **Dependencies:** Milestone 09.
- **Files Expected:** `backend/app/services/thumbnail_*.py`, `backend/app/services/metadata_*.py`.
- **Acceptance Criteria:** Generated thumbnail images are exactly 1280x720, $<2.0\text{ MB}$, and readable at mobile preview dimensions.
- **Tests:** Pillow unit test verifying dimensions, file size, and text bounding boxes.
- **Potential Risks:** Text truncation or overflow on thumbnails; mitigated by dynamic font size recalculation.
- **Definition of Done:** Project has 3 selectable thumbnail variants and a complete, formatted SEO metadata package.

---

### Milestone 11: Automated Quality Assurance Veto Gate
- **Objective:** Implement the 14-point deterministic QA verification engine that acts as an automated veto prior to publishing.
- **Features:** FFmpeg `blackdetect` and `freezedetect` filters, audio silence/clipping scanner, claim audit, license validator, similarity comparison.
- **Tasks:**
  1. Implement `QualityAssuranceService` executing all 14 deterministic tests on rendered MP4.
  2. Build automated failure reporter writing detailed diagnostics to `quality_reports`.
  3. Enforce state machine block: if any test fails, set project state to `NEEDS_ATTENTION` and abort upload.
  4. Build QA Inspector UI displaying the 14 check results with status icons and metrics.
- **Dependencies:** Milestone 10.
- **Files Expected:** `backend/app/services/quality_assurance.py`.
- **Acceptance Criteria:** System automatically halts publishing and flags errors if black frames $>0.25\text{s}$ or silence $>1.5\text{s}$ are detected.
- **Tests:** Corrupted video test verifying that a video with injected black frames is strictly vetoed.
- **Potential Risks:** False positives on intentional artistic blackouts; mitigated by tuning threshold to $>0.25$ seconds.
- **Definition of Done:** Only videos passing 100% of the 14 checks can transition to `READY_TO_PUBLISH`.

---

### Milestone 12: YouTube OAuth 2.0 & Resumable Publishing
- **Objective:** Implement Google OAuth 2.0 for YouTube, AES-256 token encryption, and chunked resumable media uploading via YouTube Data API v3.
- **Features:** Secure OAuth callback, AES-256-GCM token cipher, chunked resumable uploader (32MB chunks), scheduled publication setter.
- **Tasks:**
  1. Implement Google OAuth 2.0 flow with YouTube upload and analytics scopes.
  2. Encrypt refresh tokens before saving to database.
  3. Implement `YouTubePublishingService` with resumable upload protocol handling network interruptions.
  4. Set video title, description, tags, custom thumbnail, category ID 28, and `syntheticMedia: true`.
  5. Support scheduled publication timestamps aligned with channel cadence.
- **Dependencies:** Milestone 11.
- **Files Expected:** `backend/app/services/youtube_publishing.py`, `backend/app/utils/crypto.py`.
- **Acceptance Criteria:** Video uploads successfully to YouTube as `unlisted` or `scheduled` with correct metadata, thumbnail, and synthetic content flag.
- **Tests:** Integration test executing upload to YouTube test channel and verifying video status via YouTube Data API.
- **Potential Risks:** YouTube API quota exhaustion (10,000 units/day); mitigated by daily upload caps (max 4/day).
- **Definition of Done:** User can click "Publish" or let the automation engine successfully upload a verified video to YouTube.

---

### Milestone 13: YouTube Analytics Ingestion & Topic Optimization Loop
- **Objective:** Ingest YouTube Analytics telemetry and feed performance data back into future topic scoring algorithms.
- **Features:** YouTube Analytics API worker, retention curve parser, topic weight updater, analytics dashboard.
- **Tasks:**
  1. Implement `YouTubeAnalyticsService` polling views, watch time, CTR, and 30s retention at +24h, +48h, and +7d.
  2. Store snapshots in `analytics_snapshots` table.
  3. Implement feedback algorithm adjusting topic category weights based on retention performance.
  4. Connect frontend Analytics dashboard with retention curves and CTR charts.
- **Dependencies:** Milestone 12.
- **Files Expected:** `backend/app/services/youtube_analytics.py`, `backend/app/services/feedback_loop.py`.
- **Acceptance Criteria:** Real-time analytics display in dashboard; high-retention topics receive an automatic score boost in future discovery cycles.
- **Tests:** Feedback loop unit test verifying topic weight adjustments based on simulated retention metrics.
- **Potential Risks:** Latency in YouTube Analytics reporting (up to 48 hours); mitigated by displaying "Pending Telemetry" state in UI.
- **Definition of Done:** Channel analytics are automatically synchronized and utilized to improve future content ideas.

---

### Milestone 14: Security Hardening, Automated Testing & Deployment
- **Objective:** Harden security, configure production deployment scripts, and run end-to-end regression suites.
- **Features:** CORS restrictions, rate limiters, automated database backups, Docker containerization for worker deployment.
- **Tasks:**
  1. Implement strict rate limiting (SlowAPI) on all public and authenticated endpoints.
  2. Audit all database queries and ensure zero secret leakage in API schemas.
  3. Configure Dockerfile and docker-compose for deploying FastAPI and workers to a persistent host.
  4. Setup Vercel deployment pipeline for Next.js frontend.
  5. Run complete end-to-end test suite (`pytest` + Playwright).
- **Dependencies:** Milestone 13.
- **Files Expected:** `Dockerfile`, `docker-compose.yml`, `backend/tests/*`.
- **Acceptance Criteria:** 100% test pass rate across unit and integration tests; zero high/critical vulnerabilities in dependency scans.
- **Tests:** Security vulnerability scan (`pip-audit` / `npm audit`) and end-to-end automated pipeline test.
- **Potential Risks:** Memory spikes on worker containers; mitigated by memory limits in Docker compose.
- **Definition of Done:** System runs cleanly in a containerized environment with production-grade security headers and encryption.

---

### Milestone 15: End-to-End Autonomous Pipeline Verification & Launch
- **Objective:** Execute full unattended end-to-end automation across 1 long-form video and 1 Short, verifying the entire hands-off lifecycle.
- **Features:** Automated weekly cron trigger, autonomous topic selection, scriptwriting, voiceover, capture, rendering, QA audit, and scheduled upload.
- **Tasks:**
  1. Enable "Fully Autonomous Mode" in automation settings.
  2. Trigger end-to-end long-form video generation (6–10 minutes) on AI productivity tools.
  3. Trigger end-to-end YouTube Short generation (30–60 seconds).
  4. Verify that both videos pass the 14-point QA gate and are scheduled on YouTube.
  5. Deliver final operations runbook to channel owner Muhammad Ali.
- **Dependencies:** Milestone 14.
- **Files Expected:** `docs/OPERATIONS_RUNBOOK.md`.
- **Acceptance Criteria:** Both videos are produced and scheduled on YouTube with 100% automated execution, $0.00 external API spend, and zero human editing.
- **Tests:** Complete live production run with telemetry logging.
- **Potential Risks:** Unforeseen third-party API outage during live run; mitigated by automatic worker retry and alert logging.
- **Definition of Done:** Platform officially enters production operation for Muhammad Ali's YouTube channel.
