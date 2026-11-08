# Creator Studio AI — API Integration & Endpoint Specification

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Base URL:** `http://localhost:8000/api/v1` (Local Staging) / Cloud Proxy  
**Auth Scheme:** HTTP Bearer JWT (HS256)  

---

## 1. Overview & Architecture

All API endpoints in Creator Studio AI follow RESTful principles with JSON payloads and standard HTTP response status codes. The API layer is implemented using FastAPI 0.115 and Python 3.12, organized into 23 modular sub-routers mounted at `/api/v1`.

The frontend communicates with this API via `frontend/src/lib/api.ts`, which automatically injects Bearer JWT authentication tokens, enforces request timeouts via `AbortController`, handles multipart file uploads, and provides graceful demonstration fallbacks when backend services are offline.

---

## 2. Comprehensive Endpoint Mapping Table

| Subsystem / Router | Method | Route Path | Description | Request Payload | Response Model | Auth |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | Server heartbeat & readiness probe | None | `HealthStatus` | Public |
| **System** | `GET` | `/system/production-health` | Production pipeline watchdog & active workflows | `channel_id` (Query) | `ProductionHealthResponse` | Bearer |
| **System** | `GET` | `/system/budget-status` | Zero-dollar budget compliance & spend monitor | `channel_id` (Query) | `BudgetStatusResponse` | Bearer |
| **System** | `GET` | `/system/resource-usage` | Monthly inference, TTS, and compute breakdown | `channel_id` (Query) | `ResourceUsageSummary` | Bearer |
| **System** | `GET` | `/system/failures` | Workflow failure log and diagnostics | `limit` (Query) | `List[WorkflowFailure]` | Bearer |
| **Auth** | `POST` | `/auth/login` | User authentication & JWT issuance | `{ email, password }` | `AuthSession` | Public |
| **Auth** | `POST` | `/auth/register` | User registration & initial channel provisioning | `{ email, password, full_name }` | `AuthSession` | Public |
| **Auth** | `GET` | `/auth/me` | Authenticated user profile & active role | None | `UserRead` | Bearer |
| **Projects** | `GET` | `/projects` | List video projects with format filtering | `format, status, skip, limit` | `List[VideoProjectRead]`| Bearer |
| **Projects** | `POST` | `/projects` | Create a new long-form or Shorts video project | `{ title, format, target_duration }` | `VideoProjectRead` | Bearer |
| **Projects** | `GET` | `/projects/{id}` | Inspect single project lifecycle & stages | None | `VideoProjectDetail` | Bearer |
| **Topics** | `GET` | `/topics` | Query scored topics by niche and opportunity | `channel_id, status, min_score` | `TopicListResponse` | Bearer |
| **Topics** | `POST` | `/topics/sync` | Synchronous Gemini topic discovery & scoring | `{ channel_id, niche_override, count }` | `List[TopicResponse]`| Bearer |
| **Topics** | `POST` | `/topics/research` | Enqueue background topic research worker job | `{ channel_id, niche_override, count }` | `JobRead` (202) | Bearer |
| **Topics** | `PATCH`| `/topics/{id}/status` | Update topic state (DISCOVERED, SELECTED, ARCHIVED) | `{ status }` | `TopicResponse` | Bearer |
| **Scripts** | `GET` | `/scripts` | List generated scripts across active projects | `project_id` (Query) | `List[ScriptResponse]` | Bearer |
| **Scripts** | `POST` | `/scripts/generate` | Generate scene-partitioned script with Gemini | `{ project_id, format, target_duration }`| `ScriptResponse` | Bearer |
| **Scripts** | `POST` | `/scripts/sections/{id}/regenerate` | Refine section narration with fact-checking | `{ refinement_prompt }` | `SectionResponse` | Bearer |
| **Voice** | `GET` | `/voice/providers` | Discover active TTS engines & capabilities | None | `ProviderCapabilities` | Bearer |
| **Voice** | `GET` | `/voice/voices` | List available neural voices (Edge-TTS / Mock) | None | `List[VoiceInfo]` | Bearer |
| **Voice** | `POST` | `/voice/preview` | Generate instant 5-second audio preview | `{ voice_id, text }` | `VoicePreviewResponse`| Bearer |
| **Voice** | `POST` | `/voice/generate` | Synthesize complete master narration track | `{ project_id, voice_id, speed_ratio }` | `JobRead` (202) | Bearer |
| **Visual** | `GET` | `/visual/assets` | Browse visual asset catalog & licenses | `category, license_status` | `MediaAssetListResponse`| Bearer |
| **Visual** | `POST` | `/visual/assets/upload`| Multipart media asset upload & SHA256 check | `FormData: file, title, license_type` | `MediaAssetResponse` | Bearer |
| **Visual** | `POST` | `/visual/stock/search` | Query Pexels/Pixabay zero-cost stock media | `{ query, media_type, per_page }` | `StockSearchResult` | Bearer |
| **Visual** | `POST` | `/visual/storyboards/generate` | Generate scene visual directives from script | `{ project_id, format }` | `StoryboardResponse` | Bearer |
| **Video** | `GET` | `/video/timelines/{id}` | Inspect multi-track FFmpeg editing timeline | None | `VideoTimelineResponse`| Bearer |
| **Video** | `POST` | `/video/render` | Trigger FFmpeg video compilation & subtitles | `{ project_id, resolution, render_mode }` | `RenderJobResponse` | Bearer |
| **Thumbnails**| `POST` | `/thumbnails/generate` | Compose 3 contrasting variants (A, B, C) via PIL | `{ project_id, headline, style_preset }` | `List[ThumbnailResponse]`| Bearer |
| **Thumbnails**| `PATCH`| `/thumbnails/{id}/approve` | Select winning variant for release package | `{ approved: true }` | `ThumbnailResponse` | Bearer |
| **Metadata** | `POST` | `/metadata/generate` | Synthesize titles, chapters & synthetic disclosure | `{ project_id }` | `MetadataDraftResponse`| Bearer |
| **QA** | `POST` | `/qa/runs` | Execute 14-point deterministic QA Veto Gate | `{ project_id, run_async }` | `QARunResponse` | Bearer |
| **QA** | `POST` | `/qa/findings/{id}/resolve` | Record human correction / resolution note | `{ resolution_notes }` | `QAFindingResponse` | Bearer |
| **YouTube** | `GET` | `/youtube/status` | Verify channel OAuth connection & credentials | None | `YouTubeConnectionStatus`| Bearer |
| **YouTube** | `GET` | `/youtube/connect` | Obtain Google OAuth 2.0 authorization URL | None | `YouTubeConnectResponse`| Bearer |
| **YouTube** | `POST` | `/youtube/publish` | Dispatch resumable chunked video publication | `{ project_id, privacy, scheduled_at }` | `PublicationJobResponse`| Bearer |
| **Analytics** | `GET` | `/analytics/overview` | Channel lifetime telemetry, views, subscribers | `channel_id` (Query) | `AnalyticsOverview` | Bearer |
| **Analytics** | `POST` | `/analytics/content-strategy` | Run algorithmic feedback loop to tune weights | `{ feedback_target }` | `StrategyResponse` | Bearer |
| **Workflows** | `GET` | `/workflows` | List automated autonomous pipeline workflows | `status, limit` | `List[WorkflowRunRead]`| Bearer |

---

## 3. Error Handling Standards

All endpoints return uniform error envelopes:

```json
{
  "detail": "Description of the operational failure or validation error.",
  "error_code": "ERR_SPECIFIC_CODE",
  "status_code": 400
}
```

Standard Status Codes:
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `202 Accepted`: Task accepted and enqueued into durable PostgreSQL queue.
- `400 Bad Request`: Validation failure or malformed payload.
- `401 Unauthorized`: Missing or expired Bearer JWT token.
- `402 Payment Required`: Spend Governor triggered ($0.00 spend cap exceeded).
- `403 Forbidden`: Cross-tenant access denied or QA Veto Gate blocked.
- `404 Not Found`: Target entity does not exist.
- `409 Conflict`: Concurrency lock collision or duplicate resource.
- `502 Bad Gateway`: Upstream API provider timeout or unreachable service.
