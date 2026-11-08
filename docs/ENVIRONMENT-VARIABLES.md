# Creator Studio AI — Environment Variables Specification

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening & Official Release  
**Release Version:** v0.1.0-RELEASE  

---

## 1. Backend Environment Variables Matrix

| Variable Name | Required | Default Value | Description & Security Guidelines |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | Yes | `development` | Deployment environment: `production`, `staging`, `development`, `test`. |
| `APP_DEBUG` | No | `false` | Enables verbose debug logging. **Must be false in production**. |
| `APP_HOST` | No | `0.0.0.0` | Bind host interface for FastAPI server. |
| `APP_PORT` | No | `8000` | Port for FastAPI server. |
| `FRONTEND_URL` | Yes | `http://localhost:3000` | Allowed origin for CORS headers. In prod: `https://app.yourdomain.com`. |
| `APP_MASTER_ENCRYPTION_KEY`| Yes | None | 64-character hex key (32 bytes) for AES-256-GCM token encryption. |
| `APP_SECRET_KEY` | Yes | None | Cryptographic secret for signing internal JWT tokens. |
| `DATABASE_URL` | Yes | None | Asynchronous PostgreSQL connection string (`postgresql+asyncpg://...`). |
| `DATABASE_URL_SYNC` | Yes | None | Synchronous PostgreSQL connection string (`postgresql://...`) for Alembic migrations. |
| `SUPABASE_URL` | Yes | None | Supabase project URL (`https://xyz.supabase.co`). |
| `SUPABASE_ANON_KEY` | Yes | None | Public anonymous client key for Supabase Auth. |
| `SUPABASE_JWT_SECRET` | Yes | None | JWT signing secret from Supabase Dashboard -> Project Settings -> API. |
| `SUPABASE_SERVICE_ROLE_KEY`| No | None | Secret admin key for background auto-provisioning (never expose to frontend). |
| `GEMINI_API_KEY` | Conditional | None | Google AI Studio API key. If absent, falls back safely to `MockAIProvider`. |
| `GEMINI_MODEL_FAST` | No | `gemini-1.5-flash`| Model used for topic discovery, outlines, and summaries. |
| `GEMINI_MODEL_REASONING` | No | `gemini-1.5-pro` | Model used for deep claim verification and script breakdown. |
| `MAX_MONTHLY_SPEND_USD` | No | `0.00` | Hard spending cap. Set to `0.00` to enforce 100% Free Tier protection. |
| `FREE_TIER_RPM_LIMIT` | No | `15` | Requests per minute sliding-window limiter for Gemini free tier. |
| `FREE_TIER_RPD_LIMIT` | No | `1500` | Requests per day sliding-window limiter for Gemini free tier. |
| `TTS_ENGINE` | No | `edge-tts` | Text-to-speech engine: `edge-tts` (zero-cost high-fidelity) or `mock`. |
| `TTS_DEFAULT_VOICE` | No | `en-US-ChristopherNeural` | Default voice identifier for neural voice generation. |
| `PEXELS_API_KEY` | No | None | Pexels REST API key for commercial stock B-roll (200 req/hr, 20k req/mo). |
| `PIXABAY_API_KEY` | No | None | Pixabay REST API key for stock photos (100 req/min burst, 5,000 req/hr). |
| `YOUTUBE_CLIENT_ID` | Conditional | None | Google Cloud Console OAuth 2.0 Web Client ID. |
| `YOUTUBE_CLIENT_SECRET` | Conditional | None | Google Cloud Console OAuth 2.0 Client Secret. |
| `YOUTUBE_REDIRECT_URI` | Conditional | `http://localhost:8000/api/v1/youtube/oauth/callback` | Authorized redirect URI configured in Google Cloud Console. |
| `STORAGE_DRIVER` | No | `local` | `local` for disk storage or `r2` for Cloudflare R2 object storage. |
| `LOCAL_STORAGE_DIR` | No | `./storage` | Filesystem path for assets, renders, and temporary files. |
| `CLOUDFLARE_R2_ACCOUNT_ID` | Conditional | None | Cloudflare account ID for R2 storage. |
| `CLOUDFLARE_R2_ACCESS_KEY_ID`| Conditional | None | S3-compatible Access Key ID for Cloudflare R2. |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY`| Conditional | None | S3-compatible Secret Access Key for Cloudflare R2. |
| `CLOUDFLARE_R2_BUCKET_NAME`| Conditional | `creator-studio-ai`| R2 bucket name for persistent media assets. |
| `WORKER_ID` | No | `staging-worker-01` | Unique identifier for persistent worker process instance. |
| `WORKER_POLL_INTERVAL` | No | `2.0` | Seconds between queue polling cycles. |
| `WORKER_LEASE_SECONDS` | No | `120` | Duration of atomic job claim before watchdog reclamation. |
| `WORKER_DEFAULT_MAX_RETRIES` | No | `3` | Maximum retry attempts for transient errors before terminal fail. |

---

## 2. Frontend Environment Variables Matrix

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000/api/v1` | Public URL for backend FastAPI gateway. |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | None | Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | None | Supabase anonymous public key. |

---

## 3. Secret Generation & Key Rotation Guidelines

### Master Encryption Key (AES-256-GCM)
Generate a high-entropy 256-bit key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Application Secret Key (JWT Signing)
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Security Guardrails
1. **Never commit `.env` to version control.** Ensure `.gitignore` contains `.env` and `.env.local`.
2. **Zero secrets in client bundles:** Only variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.
3. **Audit logging redaction:** API keys and OAuth tokens are automatically masked by backend log interceptors before output.
