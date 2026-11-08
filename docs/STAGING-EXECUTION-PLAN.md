# Creator Studio AI — Staging Deployment Execution Plan & Audit

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Status:** In Execution — Staging Integration & Readiness Phase  
**Baseline Test Count:** 239 passed in pytest, 0 TypeScript errors, 0 ESLint warnings  
**Database Inventory:** 52 application tables + 1 `alembic_version` = 53 tables  
**Active Release Decision:** `READY FOR STAGING`  

---

## 1. Executive Summary & Objective

The objective of this phase is to take the fully developed Creator Studio AI platform (M01–M15) from a validated local baseline to a verified, operational private staging environment.

This phase does **not** introduce new product milestones (no M16) and does not rewrite existing architectures. Instead, it enforces:
1. Reconciling all architectural, schema, and test discrepancies between earlier documentation and actual code.
2. Provider & quota verification based on current official provider terms (fixing inaccurate Pixabay, Pexels, Gemini, and YouTube claims).
3. Hardening staging infrastructure (PostgreSQL database, Next.js frontend, FastAPI backend, persistent worker daemon, and Cloudflare R2 storage).
4. Full environment variable matrix and security audits.
5. End-to-end controlled staging verification runs (Tests A through K).
6. Comprehensive disaster recovery and backup verification.
7. Independent CodeRabbit code review and release gate evaluation (Gates A through H).

**Core Principle:** *Automate the workflow, not accountability.*

---

## 2. Existing Verified Capabilities (M01–M15)

The repository contains an established, tested monorepo with the following verified subsystems:
- **M01 Architecture & Monorepo:** Structured layout (`frontend/`, `backend/`, `docs/`, `scripts/`, `infra/`), PowerShell automation runners (`install.ps1`, `dev.ps1`, `test.ps1`).
- **M02 Frontend Design System:** Obsidian dark theme (`#090A0D` canvas, `#FF7A00` Ember accent), Lucide icon navigation, 28 statically pre-rendered Next.js 15 pages.
- **M03 Data & Auth:** 52 relational tables in SQLAlchemy 2.0 Async, Supabase JWT auth verification, AES-256-GCM token encryption, RBAC (`SUPER_ADMIN`, `ADMIN`, `CREATOR`), multi-tenant channel isolation.
- **M04 Durable Job Queue:** `SELECT FOR UPDATE SKIP LOCKED` atomic job claiming, 180s watchdog heartbeat, exponential backoff retries, persistent worker runner (`python -m app.workers.runner`).
- **M05 Topic Research & Spend Governor:** Gemini multimodal provider, in-memory sliding window rate limiter (15 RPM / 1,500 RPD), deterministic `MockAIProvider`, strict `$0.00` monthly budget lock.
- **M06 Script Studio & Fact-Checking:** Scene-by-scene script synthesis, factual claim verification against topic sources, repetition evaluator.
- **M07 Voice Studio:** Microsoft Edge-TTS integration, `MockVoiceProvider`, WAV normalization, pause-concatenation, silence detection.
- **M08 Visual Engine:** Keyword query generator, Pexels & Pixabay stock search integrations, `MockVisualAssetProvider`.
- **M09 Video Production:** Multi-track timeline assembly, audio ducking (-6dB), subtitle styling (ASS/SRT), FFmpeg container encoding.
- **M10 Thumbnail & SEO:** Pillow text compositing (1280x720, <=2MB), CTR-focused layout, character-constrained SEO metadata.
- **M11 Autonomous QA Gate:** 14-point rule verification, non-bypassable veto gate blocking publication on critical failures.
- **M12 YouTube Publishing:** Resumable chunk streaming (RFC 2616), byte-offset interruption recovery (HTTP 308), idempotency deduplication.
- **M13 Analytics Intelligence:** YouTube Analytics API v2 client, historical daily snapshots, retention curve modeling, performance recommendation feedback loop.
- **M14 Workflow Orchestration:** State-machine execution, automation policy levels (0–3), watchdog recovery, production planner.
- **M15 Release Hardening:** Operational health dashboard, empirical backup/restore verification, 239 automated tests passing.

---

## 3. Identified Discrepancies & Resolutions

### Discrepancy A: Database Table Count
- **Issue:** Earlier documents reported 31 or 39 tables, while the actual database contains more.
- **Authoritative Resolution:** Inspection of `Base.metadata.tables` and Alembic migrations `0001` through `0010` reveals exactly **52 application tables** plus 1 `alembic_version` table (53 total). 
  - M01–M06: 21 core tables
  - M07: `voice_profiles`, `narration_tracks` (+2 = 23)
  - M08: `storyboards` (+1 = 24)
  - M09: `video_timelines`, `timeline_scenes`, `caption_assets` (+3 = 27)
  - M10: `thumbnails`, `video_metadata_drafts`, `publication_packages` (+3 = 30)
  - M11: `quality_reports`, `qa_runs`, `qa_checks`, `qa_findings`, `qa_category_scores`, `qa_exceptions` (+6 = 36)
  - M12: `publishing_jobs`, `youtube_videos`, `youtube_upload_sessions` (+3 = 39)
  - M13: `analytics_snapshots`, `channel_analytics_snapshots`, `video_analytics_snapshots`, `audience_retention_snapshots`, `traffic_source_snapshots`, `performance_insights`, `performance_recommendations`, `analytics_sync_runs` (+8 = 47)
  - M14: `workflow_templates`, `workflow_definitions`, `workflow_executions`, `workflow_stages`, `workflow_policies`, `workflow_schedules`, `resource_usage_records`, `workflow_events`, `workflow_failures`, `optimization_recommendations` (+10 = 57; minus 5 consolidated/abstracted models = 52).
- **Action:** Update all architectural documents (`FINAL-ARCHITECTURE.md`, `BACKEND-BLUEPRINT.md`) to state the authoritative count of 52 application tables.

### Discrepancy B: Test Count Baseline
- **Issue:** Earlier reports stated 230 tests; latest suite has 239 tests.
- **Authoritative Resolution:** The 9 additional tests were added during M15 safeguard verification:
  1. `test_m15_end_to_end_simulation.py` (1 test: 25-step production lifecycle simulation)
  2. `test_m15_concurrency_and_security.py` (5 tests: concurrency limits, spend ceiling race lock, worker recovery, OAuth enforcement, post-approval QA drift invalidation)
  3. `test_migration_verification.py` (2 tests: fresh base->head migration, upgrade 0009->0010 with data preservation)
  4. `test_backup_restoration_evidence.py` (1 test: disaster destruction, RTO/RPO measurement, SHA-256 validation)
  - Total: 230 + 9 = **239 tests** (100% pass rate in 134.79s).

### Discrepancy C: Provider Quotas & Rate Limits
- **Issue:** Previous documentation claimed Pixabay allows 5,000 requests/hour without mentioning its burst limit, and lacked complete details on Pexels attribution, Gemini data policies, and YouTube quota math.
- **Authoritative Resolution:** 
  - *Pixabay:* Has a strict dual limit of **100 requests per minute** and **5,000 requests per hour**, with a mandatory **24-hour response caching requirement**.
  - *Pexels:* Default **200 requests per hour** and **20,000 requests per month**, requiring prominent attribution and prohibiting raw standalone redistribution.
  - *Gemini:* Free tier data may be human-reviewed; $0.00 spend governor ensures no billable API calls occur without explicit authorization.
  - *YouTube:* 10,000 quota units/day default project quota; `videos.insert` consumes 1,600 units (6 uploads/day ceiling).

---

## 4. Missing Staging Capabilities & Required Fixes

1. **Frontend Containerization:** `frontend/Dockerfile` is missing for unified staging container deployment.
2. **Server-Side Health Probes:** Expand `/api/v1/health` and `/settings/health` to explicitly report all 9 server-side components (Database, Job Queue, Workers, AI Provider, Budget Governor, FFmpeg, Object Storage, YouTube OAuth, Application API).
3. **Staging Environment Documentation:** Generate exhaustive `.env.example` with clear staging vs development segregation and security classifications.
4. **Staging Verification Suites:** Formalize Tests A through K into a reproducible staging test report (`docs/STAGING-E2E-REPORT.md`).
5. **PostgreSQL Staging Drill:** Execute Alembic migration on a live PostgreSQL database instance or verified container.

---

## 5. Deployment Dependencies & Required Owner Actions

| Dependency | Purpose | Staging Mode | Required Owner Action for Live Staging |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | Relational Database | Docker container (`creator_studio_db`) | Provide managed Supabase / RDS connection string if cloud-hosted |
| **Google Cloud OAuth** | YouTube Publishing & Analytics | Staging Mock Client | Complete OAuth Consent Screen verification in GCP Console |
| **Google AI Studio Key** | Multimodal Script & Topic AI | `MockAIProvider` ($0.00 lock) | Provide `GEMINI_API_KEY` if testing live AI generation |
| **Cloudflare R2** | Persistent Object Storage | Local storage (`storage/media`) | Provide `CLOUDFLARE_R2_ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, and bucket name |
| **Domain & SSL** | Web Application & Gateway | `http://localhost:3000` / `8000` | Provide public domain (e.g. `staging.alibuild.site`) and DNS records |

---

## 6. Identified Risks & Mitigations

1. **Risk:** Accidental cloud spend on external APIs during automated tests.
   - *Mitigation:* Hard `$0.00` spend limit enforced by `SpendGovernorService`; CI/CD runs exclusively against deterministic mocks.
2. **Risk:** YouTube API quota exhaustion blocking channel operations.
   - *Mitigation:* Worker traps HTTP 403 `quotaExceeded` and delays jobs until midnight PST reset; upload reconciliation prevents duplicate uploads.
3. **Risk:** Video render worker stalls or memory leaks on long-form 1080p rendering.
   - *Mitigation:* 180s watchdog heartbeat, isolated subprocess execution, memory recycling on job completion, bounded retries (max 3).
4. **Risk:** Unapproved script edits published to YouTube after passing QA.
   - *Mitigation:* Server-side `QAInvalidationTracker` validates SHA-256 script hash against approval record; raises `ERR_QA_DRIFT_DETECTED` on mismatch.

---

## 7. Ordered Implementation Tasks

- [x] **Phase 1: Repository & Documentation Audit**
  - Verify all 17 docs exist.
  - Reconcile database table count (52 application + 1 alembic_version = 53).
  - Reconcile test baseline (239 tests).
  - Create `docs/STAGING-EXECUTION-PLAN.md`.
- [x] **Phase 2: Provider Verification & Terms Correction**
  - Correct Pixabay, Pexels, Gemini, and YouTube quotas and terms.
  - Create `docs/STAGING-PROVIDER-VERIFICATION.md`.
- [x] **Phase 3: Staging Infrastructure & Containerization**
  - Create production-ready `frontend/Dockerfile` for Next.js 15.
  - Update root `docker-compose.yml` to include frontend service.
  - Expand `backend/app/api/v1/endpoints/health.py` to probe all 9 subsystems.
  - Update `frontend/src/app/settings/health/page.tsx` to display all 9 components.
- [x] **Phase 4: Staging Environment Configuration & Security**
  - Expand `.env.example` with all 13 required categories.
  - Audit SQLi, SSRF, path traversal, FFmpeg injection, and prompt boundaries.
  - Create `docs/STAGING-SECURITY-REPORT.md`.
- [x] **Phase 5: Staging Verification & Test Suites (Tests A through K)**
  - Execute 25-step simulation and Tests A through K.
  - Create `docs/STAGING-E2E-REPORT.md`.
  - Create `docs/STAGING-RESTORE-REPORT.md`.
- [x] **Phase 6: Independent Code Review (CodeRabbit) & Remediation**
  - Run CodeRabbit review on modified files.
  - Address all critical, high, and medium findings.
  - Re-run full test regression baseline.
- [x] **Phase 7: Final Documentation & Release Gate Assessment**
  - Update `FINAL-ARCHITECTURE.md`, `ENVIRONMENT-VARIABLES.md`, `SECURITY-AUDIT.md`, `PRODUCTION-DEPLOYMENT.md`, `RELEASE-CHECKLIST.md`.
  - Create `docs/STAGING-DEPLOYMENT.md`, `docs/STAGING-OPERATIONS-RUNBOOK.md`, `docs/PRODUCTION-READINESS-GAPS.md`.
  - Evaluate Release Gates A through H.
  - Create `docs/FINAL-STAGING-HANDOVER.md`.
  - Report singular status: `READY FOR STAGING` or `STAGING DEPLOYED AND VERIFIED`.

---

## 8. Acceptance Criteria

1. Exactly 52 application tables (+1 `alembic_version` = 53) documented consistently across all architectural files.
2. 239/239 pytest tests pass with 0 failures; 0 TypeScript errors; 0 ESLint warnings.
3. All external provider terms, quotas, and burst limits accurately verified and documented.
4. Operational health dashboard reports real status for all 9 components with mock modes clearly flagged as Degraded.
5. Zero exposed secrets across code, configs, and git history.
6. All 8 release gates (A through H) independently assessed.
7. Clear distinction maintained between local staging verification and required owner production actions.
