# Creator Studio AI — Staging Provider & External Integration Verification

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Document Status:** Formal Audit & Verification  
**Audit Date:** 2026-11-08  
**Default Spending Governor:** Enforced at **\$0.00 / month**  

---

## 1. Executive Summary

This audit inspects every external AI model, voice synthesis provider, stock media repository, video rendering tool, cloud API, and authentication service configured or integrated in Creator Studio AI.

In accordance with strict staging engineering standards:
- **No provider is assumed to be free.**
- **No unverified rate limit or quota claims are accepted.**
- **All mock provider simulations are explicitly distinguished from real live external API calls.**
- **Every billable request is subject to the hard application-level \$0.00 monthly spending lock.**

---

## 2. Comprehensive Provider Verification Matrix

| Subsystem | Provider | Official API / Model Version | Official Pricing & Quotas | Integration Status | Staging Test Mode | Known Limitations | Required Owner Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Topic Research & Drafts** | Google Gemini | `gemini-1.5-flash` (`google-genai` SDK) | Free tier: 15 RPM / 1,500 RPD / 1M TPM. Paid: \$0.075/1M input, \$0.30/1M output tokens. | Configured & Abstracted | **Deterministic Mock (`MockAIProvider`)**; 0 paid calls | Free tier allows Google to log content for model training; rate clamped by `GeminiRateLimiter`. | Provide `GEMINI_API_KEY` and authorize budget if testing live generation. |
| **Fact-Checking & QA Reasoning** | Google Gemini | `gemini-1.5-pro` (`google-genai` SDK) | Free tier: 2 RPM / 50 RPD / 32K TPM. Paid: \$1.25/1M input, \$5.00/1M output tokens. | Configured & Abstracted | **Deterministic Mock (`MockAIProvider`)**; 0 paid calls | Multi-claim verification requires multiple calls; paced via queue to prevent HTTP 429. | Authorize budget for live deep reasoning. |
| **Voice Synthesis (TTS)** | Microsoft Edge-TTS | `edge-tts` (Python websocket client) | \$0.00 (No API key or billing required). | Configured & Functional | **Local Synthesis & Mock (`MockVoiceProvider`)** | Consumer service intended for Edge browser; **no enterprise SLA**; potential IP throttling. | Migrate to Azure Cognitive Services Speech (\$16/1M chars) for high-scale enterprise uptime. |
| **Voice Synthesis (Paid)** | ElevenLabs | ElevenLabs REST API v1 | Free tier: 10,000 chars/mo. Paid: \$5–\$330+/mo. | Scaffolded / Optional | **Disabled** (Prevented by \$0.00 budget cap) | Costly per minute of long-form audio (\$0.30–\$0.50 per 10-minute video). | Provide `ELEVENLABS_API_KEY` and increase monthly spend limit if desired. |
| **Stock Video & Photo** | Pexels API | REST v1 (`api.pexels.com`) | Free: **200 requests/hour**, **20,000 requests/month**. Higher limits upon application. | Configured & Functional | **Mock Asset Provider (`MockVisualAssetProvider`)** | Must display link to Pexels; no standalone redistribution; no dataset harvesting for AI training. | Add `PEXELS_API_KEY` in staging `.env` if testing live stock downloads. |
| **Stock Imagery & Vectors** | Pixabay API | REST v1 (`pixabay.com/api`) | Free: **100 requests/minute burst**, **5,000 requests/hour**. | Configured & Functional | **Mock Asset Provider (`MockVisualAssetProvider`)** | **Must cache responses for at least 24 hours**; no automated mass scraping; burst clamped at 100 req/min. | Add `PIXABAY_API_KEY` in staging `.env` if testing live stock downloads. |
| **AI Image Generation** | Google Imagen 3 | `imagen-3.0-generate-002` | Strictly paid: ~\$0.03 per image generation. | Configured & Protected | **Disabled** (Blocked by \$0.00 spend cap) | Zero free tier; billable immediately upon invocation. | Keep disabled unless explicit budget approved. |
| **AI Image Generation (Alt)** | Pollinations.ai | `image.pollinations.ai` | Free community service. | Evaluated / Not in core pipeline | **Excluded** | No SLA, unstable latency, subject to unscheduled outages; unsuitable for production. | None. Excluded from core automated pipeline. |
| **Video Editing & Rendering** | FFmpeg / FFprobe | FFmpeg 6.x / 7.x (Local binary) | Open Source (LGPL 2.1+ / GPL). \$0.00 licensing costs. | Configured via subprocess | **Local Execution / Mock Fallback** | CPU software encoding (`libx264`) takes ~2–4 min per 10-min 1080p video; needs persistent worker. | Install FFmpeg binary on staging host and configure `FFMPEG_PATH`. |
| **Thumbnail Studio** | Pillow (PIL) | PIL 10.x+ (Local Python) | Open Source (HPND). \$0.00 licensing costs. | Implemented & Verified | **Local Python Rendering** | Limited to 2D raster compositions; runs locally with zero network dependencies. | None. Operational. |
| **YouTube Upload & Metadata** | YouTube Data API v3 | `videos.insert(uploadType=resumable)` | Free project quota: **10,000 units/day**. Video upload = **1,600 units**. Read = 1 unit. | Configured & Verified | **Mock YouTube Client (`MockYouTubeClient`)** | Maximum **6 video uploads per day** under default free quota. HTTP 429 on quota exhaustion. | Apply for Google Cloud YouTube API quota increase if publishing >6 videos/day. |
| **YouTube Analytics** | YouTube Analytics API | `v2.reports.query` | Free: 100,000 units/day default quota. | Configured & Verified | **Mock Analytics Provider (`MockAnalyticsProvider`)** | YouTube's data processing pipeline imposes a 24–48 hour reporting latency on metrics. | Complete GCP OAuth verification for `yt-analytics.readonly` scope. |
| **Object Storage** | Cloudflare R2 | S3-Compatible API | Free tier: 10 GB storage, 1M Class A operations, 10M Class B operations. Zero egress fees. | Configured (`app.services.storage`) | **Local disk storage (`./storage`)** | Staging container uses local volume by default until R2 credentials provided. | Provide `CLOUDFLARE_R2_ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, and bucket name. |
| **Authentication & IAM** | Supabase Auth / PostgreSQL | GoTrue JWT + PostgreSQL 16 | Free tier: 50,000 MAU, 500 MB database storage. | Configured & Verified | **Local JWT Verification & PostgreSQL** | RLS must be paired with application-level tenant isolation. | Provide managed Supabase project keys or run self-hosted staging PostgreSQL. |
| **Search Engine** | DuckDuckGo / Tavily | DuckDuckGo HTML / Tavily REST | DuckDuckGo: Free (no key). Tavily: 1,000 free searches/mo. | Configured (`app.services.research`) | **DuckDuckGo Zero-Credential Fallback** | HTML scraping may encounter captchas under high frequency; Tavily recommended for production. | Provide `TAVILY_API_KEY` if deeper search indexing is desired. |

---

## 3. Deep-Dive Investigation of Specific Provider Discrepancies

### 3.1 Pixabay API Rate Limits (Correction of Previous Documentation)

- **Previous Inaccurate Claim:** Earlier reports claimed Pixabay allows "5,000 requests/hour" without qualification.
- **Verified Official Terms (`pixabay.com/api/docs`):**
  1. **Dual Limit Structure:** Pixabay enforces a strict **100 requests per minute** rolling burst limit alongside a **5,000 requests per hour** overall ceiling.
  2. **Mandatory Caching Policy:** Pixabay terms explicitly require that API query results **must be cached for at least 24 hours** to prevent redundant traffic.
  3. **Tracking Headers:** Every response provides real-time quota telemetry via `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
  4. **Staging Implementation:** Creator Studio AI caches all retrieved asset metadata locally in the `media_assets` table and never performs unbuffered repeated queries.

### 3.2 Pexels API Usage Guidelines & Attribution Rules

- **Official Limits (`pexels.com/api/documentation`):**
  1. Default quota is **200 requests per hour** and **20,000 requests per month**.
  2. Higher rate limits require a formal application demonstrating an active application UI.
- **Mandatory Attribution:** Pexels terms require attributing Pexels ("Photos provided by Pexels") and crediting the photographer where feasible.
- **Machine Learning Restriction:** Pexels terms strictly prohibit using their API to build datasets to train, fine-tune, or evaluate AI/ML models. Creator Studio AI uses Pexels strictly for video B-roll presentation, never for model training.

### 3.3 Google Gemini AI Models & Data Governance

- **Configured Identifiers:** `gemini-1.5-flash` (Fast drafting and metadata) and `gemini-1.5-pro` (Fact-checking, claim verification, QA reasoning).
- **Data Privacy Reality:** On Google AI Studio free tier, Google's Terms of Service state that prompts and responses may be reviewed by human reviewers and used to train Google products. **For commercial enterprise production, channel owners must use Vertex AI or pay-as-you-go billing with enterprise data privacy.**
- **Cost Protection:** The application's `SpendGovernorService` hard-blocks billable calls whenever `MAX_MONTHLY_SPEND_USD` is `$0.00`.

### 3.4 YouTube Data API v3 Quota Mathematics

- **Daily Quota:** 10,000 units/day allocated per Google Cloud project.
- **Method-Specific Costs:**
  - `videos.insert` (resumable video upload): **1,600 units**.
  - `thumbnails.set` (thumbnail upload): **50 units**.
  - `videos.update` (metadata / tags / status): **50 units**.
  - `channels.list` / `videos.list` (reads): **1 unit**.
- **Practical Maximum:** A single video publication package consumes approximately 1,701 quota units ($1,600 + 50 + 50 + 1$).
- **Maximum Daily Uploads:** $\lfloor 10,000 / 1,701 \rfloor =$ **5 to 6 completed video publications per day**.
- **Quota Recovery:** On HTTP 403 `quotaExceeded`, the worker daemon transitions the publishing job to `PUBLISHING_FAILED_RETRYABLE` and schedules resume for 00:00 PST.

---

## 4. Distinction Between Mock Staging & Real External Integrations

To ensure 100% transparency, every test and dashboard indicator is classified:

```
┌─────────────────────────────────┬──────────────────────────────────┐
│        SIMULATED / MOCK         │           LIVE EXTERNAL          │
├─────────────────────────────────┼──────────────────────────────────┤
│ • MockAIProvider (Deterministic)│ • Google Gemini Live API         │
│ • MockVoiceProvider (Local PCM) │ • Microsoft Edge-TTS Live Stream │
│ • MockVisualAssetProvider       │ • Pexels / Pixabay Live APIs     │
│ • MockYouTubeClient (HTTP 308)  │ • YouTube Resumable Live Upload  │
│ • MockAnalyticsProvider         │ • YouTube Analytics Live API     │
│ • Local File Storage            │ • Cloudflare R2 Remote S3 Bucket │
└─────────────────────────────────┴──────────────────────────────────┘
```

**Rule Enforced:** The Operational Health Dashboard (`/settings/health`) and the API `/api/v1/health` will **NEVER** report a subsystem as a live healthy integration when running in Mock mode. Mock mode is strictly displayed with an amber `DEGRADED` badge and an explicit disclaimer.
