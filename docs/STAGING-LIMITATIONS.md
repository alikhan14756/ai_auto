# Creator Studio AI — Zero-Cost Staging Limitations & Boundaries

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Document Purpose:** Transparent Operational Constraints Matrix  
**Hosting Cost:** Strictly $0.00 / month  
**Status:** Active Constraint Specification  

---

## 1. Executive Summary

This document specifies the empirical boundaries, operational limits, and intentional tradeoffs of the **Zero-Cost Staging Topology** for Creator Studio AI. 

No system operating on genuinely free tiers offers unlimited capacity. The platform is engineered with fail-safes and circuit breakers to guarantee stability within these exact boundaries.

---

## 2. Infrastructure & Hosting Limitations

### A. Supabase Free PostgreSQL
- **7-Day Inactivity Sleep:** Supabase automatically pauses projects on the free tier after 7 consecutive days of inactivity. If paused, all database connections return connection errors until manually restored in the Supabase Dashboard.
- **500 MB Database Storage Cap:** The database holds relational metadata across all 52 tables. Binary media (audio, video, thumbnails) must **never** be stored in PostgreSQL.
- **Connection Ceiling (15 Direct Connections):** Concurrent database sessions must remain below 15. The application pools connections conservatively (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=5`).

### B. Local Workstation Host Limitations
- **Machine Availability:** The FastAPI backend and worker daemon run locally on the owner's Windows workstation. When the workstation sleeps, hibernates, or loses internet connectivity:
  - Background queue processing pauses.
  - Video rendering stops.
  - The API becomes unreachable from the GitHub Pages frontend.
- **Hardware Resources:** Laptop RAM and CPU dictate render speeds. The background worker enforces a strict ceiling of **1 concurrent render job** to protect workstation responsiveness.
- **Network Bandwidth:** Uploading rendered videos to YouTube consumes residential broadband upload bandwidth.

### C. GitHub Pages Frontend
- **Static HTML/CSS/JS Only:** GitHub Pages is a static file CDN. There is no Node.js runtime, no Next.js API routes (`route.ts`), and no server-side middleware.
- **Client-Side API Connectivity:** Browser requests must connect directly to the FastAPI API endpoint. When testing remotely, a secure tunnel (e.g., Cloudflare Tunnel) is required to bridge the browser to the local machine.

---

## 3. External API & Provider Quotas

| Provider / API | Staging Quota & Constraints | Failure Mode When Exceeded | Safeguard Enforced |
| :--- | :--- | :--- | :--- |
| **Budget Governor** | **$0.00 / month** hard spend limit. | Rejects all billable API requests. | `UsageTrackingService` raises HTTP 402 if any fee is incurred. |
| **Google Gemini (Free Tier)** | **15 RPM / 1,500 RPD** for `gemini-1.5-flash`. Prompt data may be logged by Google. | HTTP 429 Too Many Requests. | Sliding-window token bucket throttles requests; falls back to `MockAIProvider`. |
| **YouTube Data API v3** | **10,000 units / day** project default. Resumable video upload costs **1,600 units**. | HTTP 403 `quotaExceeded`. | Max 4–5 uploads/day. `YOUTUBE_DAILY_UPLOAD_LIMIT=4` enforced in application. |
| **Pexels API** | **200 req / hr** and **20,000 req / month**. Attribution to photographer mandatory. | HTTP 429 rate limit error. | In-memory response caching; AI model training prohibited per ToS. |
| **Pixabay API** | **100 req / min burst** and **5,000 req / hr**. 24-hour response caching mandatory. | HTTP 429 rate limit error. | TTL cache stores search results for 24 hours per terms of service. |
| **Edge-TTS** | Unofficial Microsoft Edge speech service. Free, but subject to throttling under heavy load. | Network connection drop. | Chunks synthesized with bounded pauses; retry logic with exponential backoff. |

---

## 4. Operational Boundaries

1. **Non-Bypassable M11 QA Veto Gate:**
   - Under no circumstances can a video project advance to YouTube publishing without an APPROVED QA run with zero blocking critical findings.
   - Any post-approval artifact alteration immediately triggers `ERR_QA_DRIFT_DETECTED` and revokes approval.
2. **Deterministic Mock Testing:**
   - Automated tests run against mock providers to ensure keyless, offline execution and zero quota exhaustion.
   - Live tests must be explicitly triggered by the owner with valid credentials in `.env`.
3. **No Automated Public Releases:**
   - Videos published to YouTube in staging default to `privacyStatus: private` or `unlisted`. No public videos are published autonomously.
