# Creator Studio AI — Production Readiness Gaps & Owner Action Items

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Document Purpose:** Pre-Production Gap Analysis & Prerequisites  
**Date:** 2026-11-08  
**Current Milestone State:** M01–M15 Completed; Staging Deployed & Verified  
**Release Designation:** `READY FOR STAGING`  

---

## 1. Executive Summary

While Creator Studio AI has achieved 100% architectural, functional, and automated test readiness (239/239 tests passing, complete schema migration, non-bypassable QA veto gate, and zero leaked secrets), **production approval is a distinct decision from staging readiness**.

In accordance with strict operational boundaries:
- Automated development environments cannot unilaterally deploy to production.
- Automated tests cannot publish public YouTube videos or incur external charges.
- Certain external infrastructure prerequisites require direct channel owner ownership.

This document itemizes every remaining prerequisite required before the channel owner transitions Creator Studio AI from private staging to public production.

---

## 2. Itemized Production Prerequisites & Owner Actions

### Gap 1: Google Cloud OAuth 2.0 Consent Screen Verification
- **Current Staging State:** Configured in Google Cloud Console under "Testing" publishing status.
- **Limitation:** In "Testing" mode, OAuth refresh tokens expire after **7 days**, and Google displays an "Unverified App" warning during authentication. Only pre-authorized test Google accounts can connect.
- **Required Owner Action:**
  1. Navigate to Google Cloud Console > APIs & Services > OAuth consent screen.
  2. Complete application branding, privacy policy URL, and terms of service URL (e.g. hosted on `alibuild.site`).
  3. Submit the app for Google verification for the scopes:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/yt-analytics.readonly`
     - `https://www.googleapis.com/auth/youtube.readonly`
  4. Once approved, refresh tokens will remain persistent without 7-day dormancy expiration.

### Gap 2: YouTube Data API v3 Quota Extension
- **Current Staging State:** Default free project quota of 10,000 units/day.
- **Limitation:** Each video upload consumes 1,600 units (plus ~101 units for thumbnail and metadata updates). The platform is mechanically limited to **5–6 video uploads per calendar day**.
- **Required Owner Action:**
  - If the planned channel schedule requires publishing more than 4–6 videos per day across multiple channels, submit a YouTube API Quota Increase Request form via the Google Cloud Console.

### Gap 3: Cloudflare R2 Persistent Object Storage Provisioning
- **Current Staging State:** Media assets are stored on the local persistent container volume (`./storage/media`).
- **Limitation:** Local filesystem storage is suitable for single-node staging, but multi-worker or cloud production deployments require centralized object storage with zero egress fees.
- **Required Owner Action:**
  1. Create an R2 bucket in Cloudflare dashboard (e.g. `creator-studio-ai-production`).
  2. Generate S3 API tokens (Access Key ID and Secret Access Key).
  3. Set `STORAGE_DRIVER=r2` in production `.env` and supply `CLOUDFLARE_R2_ACCESS_KEY_ID` and `CLOUDFLARE_R2_SECRET_ACCESS_KEY`.

### Gap 4: Production Domain, DNS & TLS Termination
- **Current Staging State:** Binds to `0.0.0.0:3000` (Frontend) and `0.0.0.0:8000` (Backend API).
- **Required Owner Action:**
  1. Point DNS A-records (e.g. `creatorstudio.alibuild.site`) to the production VPS or cloud load balancer.
  2. Configure reverse proxy (Nginx / Caddy / Cloudflare) with automatic Let's Encrypt SSL/TLS certificates.
  3. Update `FRONTEND_URL` and `NEXT_PUBLIC_API_URL` to the production HTTPS domain.

### Gap 5: Persistent Background Worker VPS
- **Current Staging State:** Docker multi-container stack running worker daemon locally.
- **Limitation:** Video compositing (FFmpeg) and audio concatenation are CPU/GPU-intensive tasks that take 2–4 minutes per video. Serverless functions (AWS Lambda, Vercel Serverless) have hard execution timeouts (15s–15m) and are unsuitable.
- **Required Owner Action:**
  - Deploy the worker container (`creator_studio_worker`) on a dedicated persistent Linux host (e.g. Hetzner, DigitalOcean, AWS EC2, or Railway Persistent Worker) with at least 4 CPU cores, 8 GB RAM, and FFmpeg installed.

### Gap 6: Commercial Speech Synthesis (Optional Scaling Upgrade)
- **Current Staging State:** Uses Microsoft Edge-TTS (`edge-tts`).
- **Limitation:** Free consumer endpoint without commercial enterprise SLA; potential risk of Microsoft IP throttling under high concurrency.
- **Required Owner Action:**
  - If the channel scales to high automated concurrency and requires 100% voice SLA, provision an Azure Cognitive Services Speech resource ($16/1M characters) or ElevenLabs paid subscription.

---

## 3. Estimated Operational Costs (Verified Pricing)

| Service Component | Free / Staging Tier | Production Scaling Cost | Billing Trigger |
| :--- | :--- | :--- | :--- |
| **Google Gemini AI** | \$0.00 (15 RPM / 1,500 RPD) | ~\$0.05 – \$0.15 per video (Flash + Pro) | Set `MAX_MONTHLY_SPEND_USD > 0.00` |
| **Voice Synthesis** | \$0.00 (Edge-TTS) | \$0.00 (Edge-TTS) or \$0.16/video (Azure Speech) | Optional Azure switch |
| **Visual B-Roll** | \$0.00 (Pexels / Pixabay) | \$0.00 (Free commercial licenses) | None (Within quotas) |
| **Thumbnail & Video**| \$0.00 (Local Pillow + FFmpeg) | \$0.00 (Open-source local execution) | None |
| **YouTube Uploads** | \$0.00 (10,000 units/day) | \$0.00 (Free up to quota; free extension) | None |
| **Object Storage** | \$0.00 (Local disk) | ~\$0.15 / month (Cloudflare R2: 10GB free) | Exceeding 10 GB stored |
| **Database** | \$0.00 (Local Postgres) | \$0.00 (Supabase free tier: 500 MB) | Exceeding 500 MB data |
| **Compute VPS** | \$0.00 (Existing machine) | ~\$10 – \$25 / month (Dedicated 4-core Linux VPS)| Production hosting |
| **TOTAL ESTIMATE** | **\$0.00 / month** | **~\$10 – \$35 / month** (Extremely cost-efficient) | Production deployment |

---

## 4. Release Authorization Boundary

**Current Status:** All software development, automated testing, security controls, and staging artifacts are 100% complete and verified.

Transition to live public production will occur once the channel owner reviews this report, fulfills the six action items above, and executes the production deployment runbook.
