# Creator Studio AI

> **Autonomous, Full-Lifecycle Faceless YouTube Production Platform**  
> Engineered for Solo Builders, Tech Educators, and Digital Media Teams.

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Current Status:** **Milestone 12 Completed & Verified (YouTube OAuth 2.0, Resumable Publishing, Scheduled Releases & M11 QA Veto Gate Active)**  
**Initial Niche:** Artificial Intelligence Tools, Developer Productivity, Practical Web Technology & Coding Tutorials  
**Production Cadence:** 2 Long-Form Videos (6–10 min) + 3 YouTube Shorts (30–60s) Weekly  

---

## 🌟 Executive Summary

**Creator Studio AI** is an enterprise-grade, self-hosted autonomous media generation engine designed to transform abstract technology concepts into polished, monetizable, policy-compliant YouTube videos and Shorts—without requiring ongoing manual video editing.

By chaining deterministic verification, multi-stage LLM reasoning (via Google Gemini), local media synthesis (FFmpeg, local neural TTS, Playwright automation), and the official YouTube Data API v3, the platform operates as a 24/7 digital production studio with a **strict zero-dollar software operational baseline**.

---

## 🏗️ Repository Architecture

The platform follows a clean, decoupled monorepo structure:

```
creator-studio-ai/
├── frontend/                   # Next.js 15 App Router, React 19, TypeScript, Tailwind CSS
│   ├── src/
│   │   ├── app/                # App router pages, layouts, and global styles
│   │   ├── components/         # Reusable UI component system
│   │   └── lib/                # Shared utilities and helpers
│   ├── package.json
│   ├── tailwind.config.ts      # Obsidian & Vivid Ember design tokens
│   └── tsconfig.json           # Path aliases (@/* -> ./src/*)
├── backend/                    # FastAPI, Python 3.12+, SQLAlchemy 2.0 Async, Alembic
│   ├── app/
│   │   ├── api/v1/             # Resource-oriented REST routers & health endpoints
│   │   ├── core/               # Configuration management & structured logging
│   │   ├── db/                 # Database engine, session lifecycle & declarative models
│   │   └── main.py             # Application entry point & CORS configuration
│   ├── alembic/                # Database schema migration environment
│   ├── tests/                  # Automated pytest test suites (5/5 unit tests passed)
│   ├── requirements.txt        # Managed Python dependencies
│   └── alembic.ini
├── docs/                       # Complete product blueprints and architectural specifications
│   ├── 00-PROJECT-REVIEW.md    # Master cross-document consistency audit
│   ├── 01-PRD.md               # Product Requirements Document
│   ├── 02-APP-FLOW.md          # Application navigation & user journey maps
│   ├── 03-UI-UX-BRIEF.md       # Design system & 21 screen blueprints
│   ├── 04-TRD.md               # Technical Requirements Document
│   ├── 05-BACKEND-BLUEPRINT.md # 21 PostgreSQL models, 21 services & state machine
│   ├── 06-IMPLEMENTATION-PLAN.md# 15-milestone roadmap & acceptance criteria
│   └── diagrams/               # Standalone Mermaid diagrams (.mmd)
├── scripts/                    # Windows PowerShell developer automation scripts
│   ├── install.ps1             # One-click environment bootstrap
│   ├── dev.ps1                 # Concurrent frontend & backend dev runner
│   └── test.ps1                # Full test suite execution runner
├── storage/                    # Persistent local media working directory (git-ignored)
│   ├── audio/                  # Mastered WAV vocals & stems
│   ├── captures/               # Playwright 1080p 60fps screen recordings
│   ├── renders/                # Assembled master MP4 video files
│   ├── thumbnails/             # 1280x720 graphical thumbnails
│   └── scratch/                # Temporary processing scratchpad
├── infra/                      # Containerization & local infrastructure
│   └── docker-compose.yml      # Local PostgreSQL 16 service
├── .env.example                # Comprehensive configuration template
├── .gitignore                  # Git exclusion rules
├── progress.txt                # Ralph Loop / GSD verified task progress log
└── README.md                   # This project guide
```

---

## 🛠️ Technology Stack

| Layer | Component | Selection & Rationale |
|:---|:---|:---|
| **Frontend** | **Next.js 15 + React 19** | TypeScript strict mode, App Router, SSR/SSG performance, Lucide icons. |
| **Styling** | **Tailwind CSS + shadcn/ui** | Obsidian dark canvas (`#090A0D`) with Vivid Ember accent (`#FF7A00`). |
| **Backend API** | **FastAPI (Python 3.12+)** | High-throughput asynchronous REST gateway with Pydantic v2 validation. |
| **Database** | **PostgreSQL 16 (via Supabase)** | Relational integrity, JSONB scene manifests, and row-level locking. |
| **ORM & Migrations** | **SQLAlchemy 2.0 + Alembic** | Async session management, connection pooling, and versioned migrations. |
| **Task Queue** | **PostgreSQL `FOR UPDATE SKIP LOCKED`** | Transactional queue inside database; eliminates Redis hosting overhead. |
| **AI LLM Engine** | **Google Gemini 1.5 Flash / Pro** | Google AI Studio free tier (15 RPM / 1,500 RPD) with token-bucket guardrails. |
| **Voice Synthesis** | **Edge-TTS / Kokoro-TTS (Local)** | High-fidelity neural voice synthesis running directly on local CPU ($0 cost). |
| **Web Recording** | **Playwright (Python Async)** | Headless Chromium recording authentic web demos at 1080p 60fps. |
| **Media Assembly** | **FFmpeg 6.x & FFprobe** | Multi-track audio ducking, kinetic ASS typography subtitles, H.264 rendering. |
| **Storage** | **Local Disk / Cloudflare R2** | Local disk in development; S3-compatible R2 ($0 egress) in production. |
| **Publishing** | **YouTube Data API v3** | Resumable chunked upload protocol with AES-256 encrypted refresh tokens. |

---

## 📋 Prerequisites

Before running the platform, ensure the following runtimes are installed on your Windows workstation:

1. **Python 3.11 or 3.12+** (Verified with Python 3.12.14).
2. **Node.js 20+ or 22+** (Verified with Node.js v26.1.0 and npm 11.13.0).
3. **Git for Windows** (Verified with git 2.53.0).
4. **FFmpeg & FFprobe** (Recommended via `winget install Gyan.FFmpeg` or `choco install ffmpeg`).

---

## 🚀 Installation & Windows Setup

### Option 1: Automated One-Click Installation (PowerShell)

Run the automated setup script from the repository root:

```powershell
.\scripts\install.ps1
```

This script will:
1. Verify Python and Node.js runtimes.
2. Create a clean Python 3.12 virtual environment at `backend\.venv`.
3. Install backend dependencies (`fastapi`, `sqlalchemy`, `alembic`, `greenlet`, `pydantic`, etc.).
4. Install frontend dependencies in `frontend/node_modules`.
5. Generate a local `.env` configuration file from `.env.example`.

### Option 2: Manual Step-by-Step Installation

#### 1. Configure Environment
```powershell
Copy-Item .env.example .env
# Edit .env and enter your Gemini API key and credentials
```

#### 2. Setup Backend Virtual Environment
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

#### 3. Setup Frontend Node Modules
```powershell
cd frontend
npm install
cd ..
```

---

## 💻 Windows Development Commands

| Task | Command (PowerShell) | Description |
|:---|:---|:---|
| **Start All Servers** | `.\scripts\dev.ps1` | Launches Backend and Frontend in separate PowerShell windows. |
| **Start Worker Daemon** | `.\scripts\worker.ps1` | Launches standalone background job worker loop. |
| **Start Backend API** | `cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000` | FastAPI server at `http://localhost:8000`. |
| **Start Frontend** | `cd frontend; npm run dev` | Next.js server at `http://localhost:3000`. |
| **Run All Tests** | `.\scripts\test.ps1` | Executes backend pytest suite (117 tests) and frontend checks. |
| **Run Backend Tests** | `cd backend; .\.venv\Scripts\pytest.exe -v` | Runs unit tests (117/117 passing). |
| **Frontend Lint** | `cd frontend; npm run lint` | Runs ESLint on frontend code. |
| **Swagger Docs** | Open browser to `http://localhost:8000/docs` | Interactive OpenAPI documentation. |
| **Health Check** | Open browser to `http://localhost:8000/api/v1/health` | Real-time system health and service telemetry. |

---

## ⚙️ Environment Configuration (`.env`)

Key configuration flags available in `.env.example`:

- `APP_ENV`: Application environment (`development` / `production`).
- `DATABASE_URL`: Asynchronous PostgreSQL connection string (`postgresql+asyncpg://...`).
- `DATABASE_URL_SYNC`: Synchronous PostgreSQL connection string for Alembic.
- `APP_MASTER_ENCRYPTION_KEY`: 32-byte hex key for encrypting YouTube OAuth tokens at rest.
- `GEMINI_API_KEY`: Google AI Studio API key (Gemini 1.5 Flash free-tier eligible).
- `MAX_MONTHLY_SPEND_USD`: Strict financial spending cap (`0.00` enforces free tier).
- `TTS_ENGINE`: Local text-to-speech engine (`edge-tts` / `kokoro-local`).
- `STORAGE_DRIVER`: Media storage driver (`local` / `cloudflare_r2`).
- `PEXELS_API_KEY`: Optional external stock provider key for commercial imagery.
- `PIXABAY_API_KEY`: Optional external stock provider key for royalty-free b-roll.

---

## 🛡️ The 14-Point Deterministic QA Veto Gate

Every video must pass 14 programmatic checks before being authorized for YouTube upload:

1. **Black Frame Threshold:** Black frame duration $\le 0.25\text{s}$.
2. **Freeze Detection:** Video freeze duration $< 2.0\text{s}$.
3. **Loudness Standards:** Audio normalized to $-14.0\text{ LUFS} \pm 1.5\text{ LUFS}$.
4. **True Peak Ceiling:** Audio max true peak $\le -1.0\text{ dBTP}$.
5. **Silence Prevention:** Zero unexpected audio dropouts $> 1.5\text{s}$.
6. **Subtitle Sync:** Caption stream duration precisely matches vocal audio length.
7. **Factual Verification:** 100% of extracted claims verified with confidence $\ge 0.80$.
8. **Asset Licensing:** All visual media verified as recorded demo, CC0, or permitted stock.
9. **Thumbnail Specifications:** Exactly 1280x720, $\le 2.0\text{ MB}$, valid JPEG/PNG.
10. **Title Length:** SEO title length $\le 95$ characters.
11. **Originality Filter:** Script transcript cosine similarity $< 70\%$ against historical uploads.
12. **Synthetic Content Disclosure:** YouTube `syntheticMedia: true` flag verified.
13. **API Quota Check:** YouTube daily upload units verified available.
14. **Budget Guardrail:** Monthly API expenditure strictly $\le$ user-defined cap ($0.00 default).

---

## 📈 Roadmap & Milestone Status

- [x] **M01: Repository Setup, Architecture Foundation & Dev Environment** — Complete & Tested.
- [x] **M02: Frontend Dashboard, Design System & Navigation** — Complete & Tested.
- [x] **M03: Database Schema, Supabase Auth & Backend REST API** — Complete & Tested (29/29 tests passed).
- [x] **M04: Durable Job Queue & Worker Daemon Engine** — Complete & Tested (46/46 tests passed).
- [x] **M05: Gemini AI Provider & Topic Research Engine** — Complete & Tested.
- [x] **M06: Script Generation & Factual Verification Studio** — Complete & Tested (80/80 tests passed).
- [x] **M07: Local Voice Generation & Audio Mastering** — Complete & Tested (98/98 tests passed).
- [x] **M08: Visual Planning, Asset Discovery & AI Image Generation** — Complete & Tested (117/117 tests passed).
- [x] **M09: FFmpeg Video Rendering & Kinetic Typography Subtitles** — Complete & Tested (133/133 tests passed).
- [x] **M10: Thumbnail Composition & YouTube SEO Metadata** — Complete & Tested (146/146 tests passed).
- [x] **M11: Deterministic Quality Assurance Veto Gate** — Complete & Tested (176/176 tests passed).
- [x] **M12: YouTube OAuth 2.0 & Resumable Publishing** — Complete & Tested (192/192 tests passed).
- [ ] **M13: YouTube Analytics Ingestion & Topic Optimization Loop**
- [ ] **M14: Security Hardening, Automated Testing & Deployment**
- [ ] **M15: End-to-End Autonomous Pipeline Verification & Launch**

---

## 👤 Owner & Production Governance

- **Project Owner:** Muhammad Ali
- **Portfolio & Contact:** [alibuild.site](https://alibuild.site)
- **Governance:** Milestone 12 is fully implemented and objectively verified with 192/192 tests passing. In accordance with strict development rules, implementation halts at M12 and does not advance into Milestone 13 without explicit owner review and approval.
