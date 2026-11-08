# Creator Studio AI — Provider, Model & Licensing Audit

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening & Official Release  
**Release Version:** v0.1.0-RELEASE  
**Audit Date:** 2026-11-08  
**Audit Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary

This audit inspects every external AI model, voice synthesis provider, stock media repository, video rendering tool, and cloud API integrated into **Creator Studio AI**. 

Under strict engineering guidelines, **no provider is assumed to be free**. This document establishes:
- The exact model identifiers and current API versions.
- Quota constraints, rate limits, and failure modes.
- Legal licensing, terms of service, and commercial suitability for YouTube monetization.
- Real billing conditions and cost-containment safeguards (including the platform's default **$0.00/month** spending lock).
- Fallback and mock provider behavior for isolated staging and continuous integration.

---

## 2. Exhaustive Provider Matrix

| Subsystem | Active Provider | Model / API Version | Commercial Licensing | Free Tier Availability | Paid Cost / Overages | Fallback / Mock Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Topic Research & Fast Drafts** | Google Gemini | `gemini-1.5-flash` | Google Generative AI ToS | 15 RPM / 1,500 RPD / 1M TPM | \$0.075 / 1M input, \$0.30 / 1M output | `MockAIProvider` (deterministic local JSON responses) |
| **Fact-Checking & QA Reasoning** | Google Gemini | `gemini-1.5-pro` | Google Generative AI ToS | 2 RPM / 50 RPD / 32K TPM | \$3.50 / 1M input, \$10.50 / 1M output | `MockAIProvider` (deterministic local JSON responses) |
| **Voice Synthesis (TTS)** | Microsoft Edge-TTS | `en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-US-JennyNeural` | Microsoft Consumer Services Agreement | Free (no API key required) | Free endpoint, but **no enterprise SLA** | `MockVoiceProvider` (synthesizes 44.1kHz PCM WAV locally) |
| **Stock Video & Photography** | Pexels API | REST v1 (`api.pexels.com`) | Pexels License (Commercial OK, no attribution required) | 200 req/hr, 20,000 req/mo | Free tier standard; enterprise custom | `MockVisualAssetProvider` (generates color gradient frames) |
| **Stock Imagery & Vectors** | Pixabay API | REST v1 (`pixabay.com/api`) | Pixabay Content License (Commercial OK) | 5,000 req/hr | Free tier standard | `MockVisualAssetProvider` (generates color gradient frames) |
| **AI Image Generation** | Google Imagen 3 | `imagen-3.0-generate-002` | Google Cloud / AI Studio ToS | None (strictly paid preview/GA) | ~\$0.03 per image (blocked by \$0.00 spend cap) | Fallback to stock search; mock generation in test mode |
| **Thumbnail Composition** | Pillow (PIL) | PIL 10.x+ (Local Python) | HPND License (Permissive Open Source) | Unlimited (runs on local CPU) | \$0.00 | Local deterministic rendering engine |
| **Video Editing & Rendering** | FFmpeg / FFprobe | FFmpeg 6.x/7.x (Local) | LGPL 2.1+ / GPL | Unlimited (runs on local CPU/GPU) | \$0.00 | Local subprocess execution; fallback to `MockVideoRenderer` |
| **YouTube Resumable Upload** | YouTube Data API v3 | `v3.videos.insert(uploadType=resumable)` | YouTube API Services Developer Policies | 10,000 units/day default project quota | Free up to quota; extension request required for >6 vids/day | `MockYouTubeClient` (full HTTP 308 chunk simulation) |
| **YouTube Channel Analytics** | YouTube Analytics API | `v2.reports.query` | YouTube API Services Terms | 100,000 units/day default quota | Free | `MockAnalyticsProvider` (historical snapshots and trends) |
| **Search & Discovery** | DuckDuckGo / Tavily | DDG HTML / Tavily Search API | Permissive Search API ToS | 1,000 req/mo on Tavily free tier | \$0.005/search on Tavily overage | Built-in DuckDuckGo zero-credential fallback |

---

## 3. Detailed Subsystem Analysis & Terms of Service

### 3.1 AI Generation & Reasoning Engine (Google Gemini)

- **Configured Models:**
  - Fast Model: `gemini-1.5-flash` (`backend/app/core/config.py`: `GEMINI_MODEL_FAST`)
  - Reasoning Model: `gemini-1.5-pro` (`backend/app/core/config.py`: `GEMINI_MODEL_REASONING`)
- **API Availability & SLA:** Available globally through Google AI Studio and Google Cloud Vertex AI.
- **Data Privacy & Training Policy:**
  - *Free Tier (AI Studio):* Google's Terms of Service state that prompts and generated content may be logged and reviewed by human reviewers to train and improve Google products. **Do not submit proprietary secrets or unreleased personal data on the free tier.**
  - *Paid Tier (Vertex AI / Pay-as-you-go with Billing):* Enterprise privacy applies; user data is not used for model training.
- **Billing & Cost Control Reality:**
  - Creator Studio AI enforces a **zero-spend governor** (`MAX_MONTHLY_SPEND_USD: 0.00`).
  - Requests evaluate `SpendGovernorService.check_spend_allowance()`. If the budget is `$0.00`, paid model calls will raise `ERR_BUDGET_EXCEEDED` before dispatch.
  - The platform includes `GeminiRateLimiter` implementing a sliding window clamp at 15 RPM to strictly prevent HTTP 429 errors on free keys.

### 3.2 Voice Studio (Microsoft Edge-TTS)

- **Configured Engine:** `edge-tts` (Python websocket client interfacing with Microsoft Speech Services).
- **Default Voices:** `en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-US-JennyNeural`.
- **Licensing & Legal Boundaries:**
  - The Edge-TTS endpoint is provided by Microsoft for the Edge browser read-aloud feature.
  - Microsoft does not provide an official commercial SLA for this endpoint.
  - While millions of creators use Edge-TTS audio for YouTube voiceovers without issue, Microsoft reserves the right to throttle, captcha, or ban automated IP addresses sending abusive volumes.
- **Production Recommendation:** For enterprise-grade scaling or channels requiring guaranteed voice consistency, users should configure an **Azure Cognitive Services Speech** resource with standard commercial pay-as-you-go billing ($16 per 1M characters).

### 3.3 Visual Asset Engine (Pexels, Pixabay, Imagen)

- **Pexels & Pixabay:**
  - Both platforms allow free commercial use on YouTube without copyright strikes.
  - Pexels API key is free; provides 200 requests/hour.
  - Pixabay API key is free; provides 5,000 requests/hour.
  - System caches media assets locally (`storage/media/`) to avoid redundant API downloads and respect upstream rate limits.
- **Google Imagen 3:**
  - Configured as an optional high-quality generative visual asset fallback when stock assets fail keyword matching.
  - **Billing Reality:** Imagen 3 carries a hard cost per image (~$0.03). It is disabled by default under the $0.00 spend cap.

### 3.4 YouTube Data API v3 & Publishing Quotas

- **Protocol:** RFC 2616 / Google Resumable Media Upload protocol.
- **Upload Quota Impact:**
  - YouTube Data API v3 grants 10,000 quota units per day per Google Cloud project.
  - `videos.insert` consumes **1,600 units**.
  - `thumbnails.set` consumes **50 units**.
  - Read calls (`videos.list`, `channels.list`) consume **1 unit**.
  - Maximum upload capacity on standard free quota: **6 videos per calendar day**.
- **Quota Exceeded Handling:**
  - When the 10,000 daily limit is reached, Google returns HTTP 403 `quotaExceeded`.
  - The durable worker traps this error, transitions the publication job to `PUBLISHING_FAILED_RETRYABLE`, records `next_retry_at` for midnight Pacific Time (PST), and alerts the creator.

### 3.5 Local Video Rendering & Thumbnail Composition

- **FFmpeg & Pillow:**
  - 100% self-hosted, open-source software running locally or inside worker containers.
  - No cloud rendering fees, no watermarks, no licensing subscriptions.
  - Render time is CPU/GPU dependent (typically 0.3x–0.5x real-time on multi-core systems).

---

## 4. Operational Recommendations for Channel Owners

1. **Keep Spend Governor Set to $0.00** during initial evaluation and testing.
2. **Apply for YouTube API Quota Extension** in Google Cloud Console if planning to publish more than 4–6 videos daily.
3. **Verify Google Cloud OAuth App:** Complete the OAuth consent screen verification to remove the 7-day token expiration limit applicable to "Testing" status apps.
4. **Use Azure Speech API** if Microsoft Edge-TTS encounters network throttling in high-volume automated environments.
