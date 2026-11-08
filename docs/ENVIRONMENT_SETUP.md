# Creator Studio AI — Environment Configuration Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Security Standard:** Zero secret leakage in client code or Git history  
**Operational Budget:** Strictly $0.00 / month  

---

## 1. Environment Architecture

Creator Studio AI separates environment configurations cleanly between root orchestration, the frontend Next.js application, and the backend FastAPI service:

```
creator-studio-ai/
├── .env.example              # Root template for monorepo automation scripts
├── frontend/.env.example     # Client-side configuration template
└── backend/.env.example      # Server-side & worker runtime configuration template
```

---

## 2. Frontend Configuration (`frontend/.env.local`)

| Variable | Description | Default (Local Staging) |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the FastAPI backend service | `http://localhost:8000` |
| `NEXT_PUBLIC_BASE_PATH` | Subdirectory path when hosting on GitHub Pages | `""` (empty for root / custom domain) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (optional client SDK) | `https://your-project.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public client anonymous Supabase key | `your-anon-key` |

> [!CAUTION]
> Never prefix private credentials, database passwords, or secret API keys with `NEXT_PUBLIC_`. Any variable starting with `NEXT_PUBLIC_` is baked into the public JavaScript bundle during `next build`.

---

## 3. Backend Configuration (`backend/.env`)

### Database & Security
```bash
# PostgreSQL async connection (used by FastAPI and asyncpg worker pool)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_ID.supabase.co:5432/postgres

# Synchronous connection (used by Alembic migrations & psycopg2)
SYNC_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_ID.supabase.co:5432/postgres

# JWT Signing Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=generate_a_random_32_byte_hex_string_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AES-256 Encryption Key for credential column protection (must be 32 bytes hex)
ENCRYPTION_KEY=generate_a_random_32_byte_hex_string_here
```

### Free-Tier AI & Media Providers
```bash
# Google Gemini (Free tier with 15 RPM / 1,500 RPD)
GEMINI_API_KEY=your_gemini_api_key_from_aistudio_google_com
GEMINI_MODEL_FAST=gemini-1.5-flash
GEMINI_MODEL_REASONING=gemini-1.5-pro

# Free Stock Media Providers (Zero-cost API keys)
PEXELS_API_KEY=your_free_pexels_api_key
PIXABAY_API_KEY=your_free_pixabay_api_key

# Text-to-Speech Engine (Default: edge-tts for zero-cost neural speech)
DEFAULT_VOICE_PROVIDER=edge-tts
DEFAULT_VOICE_ID=en-US-ChristopherNeural
```

### Spend Governor & Resource Limits
```bash
# Hard budget circuit breaker (rejection if exceeded)
MONTHLY_BUDGET_USD=0.00
ENFORCE_ZERO_DOLLAR_BUDGET=true

# Free tier rate limits
FREE_TIER_RPM_LIMIT=15
FREE_TIER_RPD_LIMIT=1500
```

### YouTube OAuth 2.0 Credentials
```bash
YOUTUBE_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_oauth_client_secret
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/v1/youtube/callback
```
