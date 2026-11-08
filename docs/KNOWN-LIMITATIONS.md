# Creator Studio AI — Known Limitations and Operational Constraints

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening & Official Release  
**Release Version:** v0.1.0-RELEASE  

---

## 1. Operational & Infrastructure Boundaries

1. **Hardware & Rendering Performance:**
   - On commodity local hardware (e.g., development laptops), FFmpeg operates using the standard CPU software encoder (`libx264`, `libopus`).
   - Rendering a 10-minute 1080p60 video takes approximately 2–4 minutes depending on CPU core count.
   - For high-volume production deployments, worker containers should be hosted on a persistent Linux VPS with NVMe storage and optional GPU hardware acceleration (`h264_nvenc`).

2. **External YouTube Data API v3 Quota Limits:**
   - Default Google Cloud projects receive 10,000 quota units per day.
   - YouTube `videos.insert` (video upload) consumes **1,600 units** per upload.
   - Consequently, default quotas support a maximum of **6 autonomous video uploads per calendar day**.
   - Channels requiring higher publishing volume must apply for an official YouTube API quota extension in the Google Cloud Console.

3. **Google Gemini Free Tier Quotas:**
   - Free tier keys enforce a sliding window limit of **15 requests per minute (RPM)** and **1,500 requests per day (RPD)**.
   - The platform includes a built-in sliding window rate limiter (`GeminiRateLimiter`) that clamps requests to avoid HTTP 429 rate limit errors.
   - Long-form scripts and deep claim verification consume multiple reasoning calls; automated batching paces invocations to remain within free tier limits.

4. **Media Storage & Disk Pruning:**
   - Long-form 1080p60 MP4 masters average 200–350 MB per video.
   - Raw visual assets, stock B-roll clips, and interim WAV voiceovers consume additional storage.
   - Platforms running local disk storage (`STORAGE_DRIVER=local`) should retain master renders indefinitely while pruning intermediate cached files after 30 days.
   - For multi-instance cloud deployments, configure Cloudflare R2 (`STORAGE_DRIVER=r2`) for unlimited object storage without egress fees.

5. **OAuth 2.0 Token Dormancy & Re-Authentication:**
   - In accordance with Google Cloud security policies, refresh tokens for apps in "Testing" mode expire after 7 days, and unverified apps expire after 6 months of inactivity.
   - If an OAuth refresh token expires or is revoked in the channel's Google Security dashboard, automated uploads will be paused, and the creator will be notified via the dashboard to reconnect their channel.

6. **Strict Zero-Dollar Spend Governor ($0.00 Cap):**
   - By default, all channel workspaces are initialized with a monthly spending limit of `$0.00`.
   - The platform defaults to free tools: local Edge-TTS for audio, open-source FFmpeg for rendering, and free-tier Gemini models.
   - If a creator chooses to integrate paid commercial providers (e.g., ElevenLabs, Midjourney API, Claude 3.5 Sonnet), they must explicitly increase their spending limit in `/settings/usage`.
