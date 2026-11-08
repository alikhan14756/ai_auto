# CREATOR STUDIO AI — ENVIRONMENT VARIABLES GUIDE

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**Security Status:** Never commit live `.env` files. Secrets must remain private.

---

## 1. Backend Environment Variables (`backend/.env`)

| Variable | Required | Default | Security Level | Purpose |
| :--- | :---: | :--- | :---: | :--- |
| `APP_NAME` | No | `Creator Studio AI` | Public | Application name in OpenAPI docs |
| `APP_ENV` | Yes | `development` | Public | Environment (`development`, `staging`, `production`) |
| `APP_DEBUG` | No | `false` | Public | Enables verbose SQL logging if true |
| `API_V1_PREFIX` | No | `/api/v1` | Public | Prefix for API router endpoints |
| `SECRET_KEY` | **Yes** | `[random-64-hex]` | **CRITICAL** | Signing secret for internal auth & CSRF tokens |
| `TOKEN_ENCRYPTION_KEY` | **Yes** | `[random-32-hex]` | **CRITICAL** | AES-256-GCM encryption key for channel tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `10080` (7 days) | Low | Lifetime of user auth sessions |
| `FRONTEND_URL` | Yes | `http://localhost:3000` | Public | Main origin of the frontend web application |
| `ALLOWED_ORIGINS` | Yes | `["http://localhost:3000"]` | Low | JSON list or comma-separated origins for CORS |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://...` | **CRITICAL** | Async connection string for FastAPI runtime |
| `DATABASE_URL_SYNC` | **Yes** | `postgresql://...` | **CRITICAL** | Sync connection string for Alembic migrations |
| `DB_POOL_SIZE` | No | `4` | Low | Max active connections in SQLAlchemy pool |
| `DB_MAX_OVERFLOW` | No | `2` | Low | Max overflow connections |
| `DB_POOL_TIMEOUT` | No | `30` | Low | Connection timeout in seconds |
| `SUPABASE_URL` | Optional | `None` | Public | Supabase project URL (`https://*.supabase.co`) |
| `SUPABASE_ANON_KEY` | Optional | `None` | Low | Supabase client anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | `None` | **CRITICAL** | Supabase service key for administrative tasks |
| `SUPABASE_JWT_SECRET` | Optional | `None` | **CRITICAL** | JWT secret to decode Supabase auth tokens |
| `GEMINI_API_KEY` | **Yes** | `None` | **CRITICAL** | Google Gemini API key for AI generation |
| `GEMINI_MODEL_FAST` | No | `gemini-1.5-flash` | Public | Fast model for summarization & metadata |
| `GEMINI_MODEL_REASONING` | No | `gemini-1.5-pro` | Public | Deep reasoning model for script evaluation |
| `MAX_MONTHLY_SPEND_USD` | Yes | `0.00` | Public | Hard budget limit for external AI services |
| `MAX_DAILY_SPEND_USD` | Yes | `0.00` | Public | Daily spend governor threshold |
| `FREE_TIER_RPM_LIMIT` | No | `15` | Public | Gemini free tier rate limit per minute |
| `FREE_TIER_RPD_LIMIT` | No | `1500` | Public | Gemini free tier rate limit per day |
| `YOUTUBE_CLIENT_ID` | Optional | `None` | Low | Google OAuth client ID for YouTube |
| `YOUTUBE_CLIENT_SECRET` | Optional | `None` | **CRITICAL** | Google OAuth client secret |
| `YOUTUBE_REDIRECT_URI` | Optional | `http://localhost:8000/...` | Low | OAuth callback endpoint |
| `LOCAL_STORAGE_DIR` | No | `storage` | Public | Directory for rendered files and assets |
| `THUMBNAIL_OUTPUT_DIR` | No | `storage/thumbnails` | Public | Directory for generated thumbnails |
| `VIDEO_RENDERER_DEFAULT_MODE`| No | `auto` | Public | Render engine (`auto`, `ffmpeg`, `mock`) |

---

## 2. Frontend Environment Variables (`frontend/.env.local`)

| Variable | Required | Default | Security Level | Purpose |
| :--- | :---: | :--- | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000` | Public | URL of backend API server |
| `NEXT_PUBLIC_SUPABASE_URL` | Optional | `""` | Public | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`| Optional | `""` | Public | Supabase anonymous API key |

> [!CAUTION]
> **Secret Hygiene Rules:**
> 1. Never put private keys, database passwords, or service role keys in `NEXT_PUBLIC_*` variables.
> 2. `frontend/.env.local` and `backend/.env` are listed in `.gitignore` and must never be committed to Git.
> 3. For local setup, copy `.env.example` templates to `.env` or `.env.local`.

---

## 3. Example Sanitized `.env` Configurations

### Backend (`backend/.env`)
```env
APP_NAME="Creator Studio AI"
APP_ENV=development
APP_DEBUG=false
SECRET_KEY=e4f8d9b1c2a34567890abcdef1234567890abcdef1234567890abcdef1234567
TOKEN_ENCRYPTION_KEY=0123456789abcdef0123456789abcdef
ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","https://alikhan14756.github.io"]
FRONTEND_URL=http://localhost:3000

# Local PostgreSQL Example
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/creator_studio_ai
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/creator_studio_ai

# Google Gemini AI (Free Tier)
GEMINI_API_KEY=AIzaSyD_EXAMPLE_KEY_REPLACE_WITH_REAL
MAX_MONTHLY_SPEND_USD=0.00
MAX_DAILY_SPEND_USD=0.00
```

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
