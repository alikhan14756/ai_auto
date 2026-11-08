# Creator Studio AI — Final Production Architecture Blueprint

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening, Deployment & Official Release  
**Status:** Verified Architecture & Staging Baseline  
**Release Version:** v0.1.0-RELEASE  

---

## 1. System Overview & Macro Topography

Creator Studio AI is an autonomous, full-lifecycle digital video production platform engineered to operate as a self-directed, deterministic content team for YouTube channels.

The architecture covers the complete lifecycle:
```
Market Ideation ──► Research Evidence ──► Structured Scripting ──► Factual Verification
       │
       ▼
Neural Voiceover ──► Visual Storyboarding ──► FFmpeg Compositing ──► Thumbnail & SEO
       │
       ▼
M11 QA Veto Gate ──► M12 YouTube OAuth Upload ──► M13 Analytics Snapshots ──► M14 Optimization
```

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Next.js 15 App Router Frontend (React 19)                       │
│    Obsidian Dark Theme (#090A0D) • Ember Accent (#FF7A00) • 28 Pre-Rendered Routes     │
│    Admin System Health Dashboard • Automation Command Center • Interactive Studios    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTPS / Bearer JWT / Server-Sent Events
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Asynchronous Gateway (Backend)                         │
│   23 Modular API Routers • Rate Limiting • Security Headers • Nonce-Verified Encryption │
│   Supabase Auth Sync • Spending Governors ($0.00 Default) • Audit Logging Interceptor  │
└───────────────┬───────────────────────────┬────────────────────────────┬───────────────┘
                │                           │                            │
                ▼                           ▼                            ▼
┌──────────────────────────────┐ ┌─────────────────────────┐ ┌──────────────────────────┐
│   PostgreSQL 16 Schema       │ │ Durable Queue Engine    │ │ AI Model Provider Engine │
│   52 Relational Tables       │ │ SKIP LOCKED Leases      │ │ Google Gemini 1.5 Flash  │
│   Async SQLAlchemy 2.0+      │ │ 180s Watchdog Heartbeat │ │ Deterministic Offline    │
│   ACID Transactions          │ │ Bounded Crash Recovery  │ │ Zero-Cost Local Fallback │
└──────────────────────────────┘ └───────────┬─────────────┘ └──────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Persistent Worker Daemon Subsystem                              │
│   Video Production Orchestrator • FFmpeg 7.x 60fps Pipeline • Edge-TTS Audio Engine   │
│   Resumable YouTube Publishing • Autonomous Policy Engine • Watchdog Heartbeats        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Technology Stack & Boundaries

| Layer | Technology | Version | Architectural Role |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | Next.js | 15.5.29 | Server-side rendered application shell with React 19 client studios |
| **Frontend Language** | TypeScript | 5.x | Strict null safety, comprehensive domain interfaces |
| **Styling Engine** | Tailwind CSS | 3.4.1 | Custom Obsidian dark-first visual palette (`#090A0D` canvas, `#FF7A00` ember) |
| **Icons & Visuals** | Lucide React | 0.359.0 | Unified accessible iconography across all 28 views |
| **Backend Framework** | FastAPI | 0.162.1 | Asynchronous typed REST service gateway with OpenAPI v3 auto-generation |
| **Python Runtime** | Python | 3.12.14 | Strong type-hinting, native asyncio, modern datetime timezone handling |
| **Database ORM** | SQLAlchemy | 2.1.8 (Async) | Async engine with asyncpg driver, strict foreign key constraints |
| **Database Engine** | PostgreSQL | 16 | Relational storage, ACID guarantees, transactional row-level locking |
| **Task Queue** | Queue Engine | Custom | Durable `FOR UPDATE SKIP LOCKED` transactional queue with 120s worker leases |
| **AI Inference** | Google GenAI SDK | 3.0.0 | Structured Gemini 1.5 Flash (free tier), Gemini 1.5 Pro, local mock provider |
| **Audio Synthesis** | Edge-TTS / FFmpeg | 6.x / 7.x | Mastered loudness (-14 LUFS, $\le -1.0$ dBTP) & neural speech synthesis |
| **Video Compositing** | FFmpeg | 7.x | Multi-track 1080p/4K 60fps rendering, audio ducking, subtitle burning |
| **Authentication** | Supabase Auth + PyJWT | 2.10.1 | Cryptographic JWT verification, auto-provisioning & RBAC |
| **Encryption Engine** | Cryptography (AES-GCM)| 46.0.7 | Authenticated AES-256-GCM encryption with 96-bit nonces for OAuth tokens |

---

## 3. Database Domain Topology (Authoritative: 52 Relational Tables)

The database schema is verified across all Alembic migrations (`0001` through `0010`) and SQLAlchemy models, consisting of exactly 52 application tables (plus 1 `alembic_version` system migration tracking table):

### A. Identity, Channels & Governance
1. **`users`**: Platform administrators and creators mapped to Supabase authentication UIDs.
2. **`channels`**: YouTube channel workspaces with AES-256-GCM encrypted OAuth tokens.
3. **`channel_settings`**: Publishing cadences, niche tags, and default spend caps ($0.00).
4. **`audit_logs`**: Immutable, append-only operational audit trail for compliance.

### B. Topic Research & Evidence
5. **`topics`**: Algorithmic topic candidates with opportunity, volume, and competition scores.
6. **`research_sources`**: Authoritative evidence sources, scraped web content, and fact citations.

### C. Projects, Scripts & Fact-Checking
7. **`video_projects`**: End-to-end video production state machine container.
8. **`scripts`**: Scene-partitioned video scripts with revision versions.
9. **`scenes`**: Individual narrative scenes with voiceover text and visual directions.
10. **`script_claims`**: Fact-checked claims with confidence scores, verification status, and citation URLs.

### D. Audio, Media, Storyboarding & Video Timelines
11. **`voice_profiles`**: Configured voice identities with speech rates and provider mappings.
12. **`voiceovers`**: Synthesized audio voiceover entity records.
13. **`narration_tracks`**: Mastered audio WAV tracks with loudness telemetry.
14. **`media_assets`**: Captured B-roll, screenshots, and stock clips with license tracking.
15. **`storyboards`**: Visual storyboard compositions matching narrative beats.
16. **`video_timelines`**: Multi-track video editing timelines with resolution and frame rate.
17. **`timeline_scenes`**: Positioned visual and audio segments on the render timeline.
18. **`caption_assets`**: Compiled subtitle tracks (.srt, .ass) with timecoded styling.
19. **`render_jobs`**: FFmpeg video rendering execution records and progress telemetry.

### E. Thumbnails, Metadata & Publication Packages
20. **`thumbnails`**: Composed thumbnail variations with font overlays and CTR predictions.
21. **`video_metadata_drafts`**: YouTube SEO titles, descriptions, tags, and category mappings.
22. **`publication_packages`**: Atomic release bundles tying video, thumbnail, and SEO together.

### F. Quality Assurance & Veto Gate (M11)
23. **`quality_reports`**: 14-point pre-publish deterministic audit results.
24. **`qa_runs`**: Comprehensive multi-category QA evaluation execution runs.
25. **`qa_checks`**: Individual validator check executions and scores.
26. **`qa_findings`**: Specific defects, policy violations, or optimization alerts.
27. **`qa_category_scores`**: Normalized category sub-scores (0–100 scale).
28. **`qa_exceptions`**: Authorized QA veto overrides with audit justifications.

### G. YouTube Publishing & Distribution (M12)
29. **`publishing_jobs`**: Resumable YouTube upload sessions and background publishing tasks.
30. **`youtube_videos`**: Deployed YouTube video records, video IDs, and live URLs.
31. **`youtube_upload_sessions`**: Resumable upload session state tracking with byte offsets.

### H. Analytics & Performance Intelligence (M13)
32. **`analytics_snapshots`**: Generic historical analytics records.
33. **`channel_analytics_snapshots`**: Channel-level daily telemetry (views, watch time, subscribers).
34. **`video_analytics_snapshots`**: Video-level performance metrics, CTR, and 30s retention.
35. **`audience_retention_snapshots`**: Second-by-second audience retention curves.
36. **`traffic_source_snapshots`**: Ingested YouTube traffic sources breakdown.
37. **`performance_insights`**: Algorithmic classification of video performance vs channel benchmarks.
38. **`performance_recommendations`**: Topic and format improvement recommendations.
39. **`analytics_sync_runs`**: Historical sync run audit logs.

### I. Autonomous Orchestration & Workflow Policies (M14)
40. **`workflow_templates`**: Standard blueprint templates (Breaking News, Deep Explainer, Shorts).
41. **`workflow_definitions`**: Channel-customized pipeline stage DAG definitions.
42. **`workflow_executions`**: End-to-end automated pipeline runs.
43. **`workflow_stages`**: Granular execution steps with dependency DAGs and status.
44. **`workflow_policies`**: Automation level tiers (0–3), safety ceilings, and human review gates.
45. **`workflow_schedules`**: Cron-like recurring workflow triggers respecting calendar cadences.
46. **`resource_usage_records`**: Granular resource consumption records.
47. **`workflow_events`**: Immutable event stream tracking state changes and transitions.
48. **`workflow_failures`**: Persistent incident records with classification and suggested resolutions.
49. **`optimization_recommendations`**: Closed-loop recommendations derived from analytics data.

### J. Jobs, Templates & Cost Governance
50. **`automation_jobs`**: Transactional worker queue job records with SKIP LOCKED leases and retries.
51. **`prompt_templates`**: Versioned system and user prompt engineering templates.
52. **`provider_usages`**: Granular token consumption and cost accounting records per channel.

---

## 4. API Router Directory (23 FastApi Routers)

All API routers are mounted under `/api/v1` with unified exception handling and JSON formatting:

| Route Prefix | Module | Purpose |
| :--- | :--- | :--- |
| `/health`, `/ready` | `endpoints/health.py` | System uptime, DB connection driver, and readiness probes |
| `/auth` | `endpoints/auth.py` | Supabase JWT token verification, login, registration, and refresh |
| `/users` | `endpoints/users.py` | User profile retrieval, RBAC role inspection |
| `/channels` | `endpoints/channels.py` | Channel workspace management and settings persistence |
| `/projects` | `endpoints/projects.py` | Video production projects state machine lifecycle |
| `/jobs` | `endpoints/jobs.py` | Durable task queue job inspection and manual retry |
| `/topics` | `endpoints/topics.py` | Algorithmic topic discovery, scoring, and research evidence |
| `/providers` | `endpoints/providers.py` | AI provider configuration, Gemini key verification, and status |
| `/scripts` | `endpoints/scripts.py` | Script generation, scene breakdown, and factual claim verification |
| `/voice` | `endpoints/voice.py` | Neural TTS audio generation, loudness normalization (-14 LUFS) |
| `/visual` | `endpoints/visual.py` | Visual asset planning, storyboarding, and media library |
| `/video` | `endpoints/video.py` | Video timeline compositing and FFmpeg rendering jobs |
| `/thumbnails` | `endpoints/thumbnails.py` | Thumbnail composition, typography overlays, and A/B variations |
| `/metadata` | `endpoints/metadata.py` | YouTube SEO title generation, description formatting, and tags |
| `/publication` | `endpoints/publication.py` | Atomic publication package staging and locking |
| `/qa` | `endpoints/qa.py` | M11 Quality Assurance evaluation, 14-point check, and veto verdicts |
| `/youtube` | `endpoints/youtube.py` | YouTube OAuth 2.0 flow, resumable chunked video upload, publish |
| `/analytics` | `endpoints/analytics.py` | YouTube channel/video performance intelligence, CTR, retention |
| `/workflows` | `endpoints/workflows.py` | Autonomous workflow executions, stage progression, pause/resume |
| `/workflow-templates`| `endpoints/workflow_templates.py`| Workflow template blueprints (Long-form, Shorts, Recovery) |
| `/automation` | `endpoints/automation.py` | Channel automation level policy configuration (Tiers 0–3) |
| `/planning` | `endpoints/planning.py` | Production schedule planning and content opportunity discovery |
| `/system` | `endpoints/system.py` | Production health monitoring, watchdog alerts, and spend governors |

---

## 5. Security & Safety Subsystems

1. **Strict $0.00 Monthly Spend Governor (`ResourceGovernor` & `UsageTrackingService`)**:
   - Default spending limit is hard-coded to `$0.00`.
   - Before executing billable inferences or operations, available balance is strictly verified.
   - Any paid operation without explicit budget authorization is blocked with `HTTP 402 Payment Required`.
2. **Non-Bypassable M11 QA Veto Gate (`PolicyEngine` & `QARun`)**:
   - Publishing authorization via `PolicyEngine.validate_publishing_authorization()` strictly requires:
     - QA evaluation score $\ge 70.0 / 100$.
     - Veto verdict equals `"APPROVED"`.
   - Without an approved QA evaluation, publishing cannot proceed under any automation tier.
3. **AES-256-GCM OAuth Token Encryption (`app.core.security`)**:
   - YouTube OAuth refresh tokens are encrypted at rest using 256-bit AES-GCM with distinct 96-bit nonces.
   - Ciphertexts cannot be decrypted without the master encryption key; tampering throws authenticated tag mismatch exceptions.
4. **Autonomous Watchdog & Crash Recovery (`ProductionHealthMonitor`)**:
   - Detects worker crashes and stalled stages using a 180-second heartbeat cutoff.
   - Automatically executes bounded retries (maximum 3 attempts) before escalating to human attention.
   - Prevents cascading failures through exponential backoff.

---

## 6. Official Release Verification Summary

- **Backend Pytest Suite:** 231 tests passing (100% success rate, 0 failures, 0 errors).
- **End-to-End Simulation:** 25-step production lifecycle test (`test_m15_end_to_end_simulation.py`) verified passing.
- **Frontend Typecheck:** 0 TypeScript compiler errors (`tsc --noEmit`).
- **Frontend Lint:** 0 ESLint warnings (`next lint`).
- **Next.js Production Build:** 28 static pages successfully compiled and bundled.
- **Spend Governor:** Hard $0.00 ceiling actively verified.
