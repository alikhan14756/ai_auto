# CREATOR STUDIO AI — API INTEGRATION & CONTRACT REPORT

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**FastAPI Prefix:** `/api/v1`  
**Total Endpoints Registered:** 110  
**Router Tags:** 17  
**Contract Status:** 100% Verified & Aligned

---

## 1. Overview & Router Index

The Creator Studio AI backend exposes a comprehensive RESTful API built on FastAPI and Pydantic v2:

| Router Prefix | Tag Name | Endpoints Count | Key Functionality |
| :--- | :--- | :---: | :--- |
| `/api/v1/health` | Health & System | 3 | Subsystem health indicators, liveness, readiness |
| `/api/v1/auth` | Authentication | 4 | Register, login, token refresh, current user profile |
| `/api/v1/users` | Users | 3 | Profile updates, settings, role checks |
| `/api/v1/channels` | Channels | 5 | Channel metadata, connected YouTube status, settings |
| `/api/v1/projects` | Video Projects | 6 | Project creation, status progression, deletion |
| `/api/v1/topics` | Topic Research | 6 | Proposals, scoring, keyword expansion, approval |
| `/api/v1/scripts` | Script Studio | 8 | 3-act generation, claims fact-checking, section regeneration |
| `/api/v1/voice` | Voice Studio | 7 | Narration profiles, synthesis, multi-track audio mix |
| `/api/v1/visuals` | Visual Planning | 8 | Storyboard scenes, asset searching, licensing verification |
| `/api/v1/video` | Video Studio | 7 | Timeline creation, scene reordering, FFmpeg render triggers |
| `/api/v1/thumbnails` | Thumbnail Studio | 7 | Layered synthesis, variant selection, validation |
| `/api/v1/seo` | SEO Metadata | 5 | Title proposals, description generation, tag optimization |
| `/api/v1/qa` | Quality Assurance | 6 | 14-point evaluation, finding resolution, admin exceptions |
| `/api/v1/youtube` | YouTube Publishing | 8 | OAuth 2.0 flow, resumable chunked upload, publish status |
| `/api/v1/analytics` | YouTube Analytics | 7 | Daily snapshots, video metrics, retention curves, feedback loop |
| `/api/v1/workflows` | Orchestration | 8 | Lifecycle state machine, stage dispatch, approvals |
| `/api/v1/jobs` | Durable Queue | 5 | Job status, queue telemetry, manual retry triggers |

---

## 2. API Contract Alignments & Backwards Compatibility

During integration verification, 7 API contract alignments were implemented with backwards compatibility:

### 2.1. YouTube Channel Status
- **Official Route:** `GET /api/v1/youtube/connection`
- **Frontend Compatible Alias:** `GET /api/v1/youtube/status`
- **Response Schema:** `YouTubeConnectionStatusResponse`
- **Output:** `{ "connected": bool, "channel_id": UUID, "title": str, "subscriber_count": int, ... }`

### 2.2. YouTube Video Publication
- **Official Route:** `POST /api/v1/youtube/publications`
- **Frontend Compatible Alias:** `POST /api/v1/youtube/publish`
- **Request Body:** `{ "privacy": "unlisted", "scheduled_at": "ISO-8601" }`
- **Server Handling:** Auto-resolves active `project_id`, `channel_id`, and `publication_package_id` if omitted.

### 2.3. YouTube Channel Disconnect
- **Route:** `POST /api/v1/youtube/disconnect`
- **Parameters:** `channel_id: Optional[UUID] = Query(None)`
- **Behavior:** Revokes credentials and deactivates channel. If `channel_id` is omitted, targets the user's active channel.

### 2.4. Video Rendering
- **Official Route:** `POST /api/v1/video/renders`
- **Frontend Compatible Alias:** `POST /api/v1/video/render`
- **Request Body:** `{ "resolution": "1080p", "aspect_ratio": "16:9", "render_mode": "auto" }`
- **Server Handling:** Automatically resolves the active project's latest timeline if `timeline_id` is omitted.

### 2.5. Thumbnail Variant Selection & Approval
- **Official Route:** `POST /api/v1/thumbnails/{thumbnail_id}/select`
- **Frontend Compatible Alias:** `PATCH /api/v1/thumbnails/{thumbnail_id}/approve`
- **Parameters:** Accepts both standard UUID and variant code strings ("A", "B", "C").

### 2.6. Script Section Regeneration
- **Official Route:** `POST /api/v1/scripts/{script_id}/regenerate-section`
- **Frontend Compatible Alias:** `POST /api/v1/scripts/sections/{section_id}/regenerate`
- **Request Body:** `{ "refinement_prompt": "Enhance technical clarity" }`
- **Server Handling:** Resolves the script and regenerates the specified narrative section while preserving adjacent text.

### 2.7. QA Finding Administrative Exception
- **Official Route:** `POST /api/v1/qa/findings/{finding_id}/exception`
- **Frontend Compatible Alias:** `POST /api/v1/qa/exceptions`
- **Request Body:** `{ "finding_id": UUID, "justification": "Business override reason" }`

---

## 3. CORS & Cross-Origin Communication

CORS headers are managed dynamically in `app/core/config.py`:
- `ALLOWED_ORIGINS` defaults:
  - `http://localhost:3000` (Local Next.js)
  - `http://127.0.0.1:3000`
  - `https://alikhan14756.github.io` (Public Staging Shell)
  - Configurable via `ALLOWED_ORIGINS` environment variable for custom production domains.
- Exposed Headers: `Content-Disposition`, `X-Total-Count`, `X-Request-ID`.
