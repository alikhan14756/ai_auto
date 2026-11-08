# Creator Studio AI

> **Autonomous, Full-Lifecycle Faceless YouTube Content Production Platform**  
> Engineered for Solo Builders, Tech Educators, and Digital Media Studios.

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**GitHub Repository:** [github.com/alikhan14756/ai_auto](https://github.com/alikhan14756/ai_auto)  
**Current Status:** **M01–M15 Full-Lifecycle Production Architecture Completed & Verified (Staging Ready)**  
**Target Cadence:** 2 Long-Form Technical Videos (6–10 min) + 3 YouTube Shorts (30–60s) Weekly  
**Operational Cost:** Strictly **$0.00 / month** Software Baseline (Free Tier & Local-First Execution)  

---

## 🌟 Executive Summary

**Creator Studio AI** is an enterprise-grade autonomous YouTube video production system that coordinates the complete media lifecycle from initial topic ideation to published, monetizable YouTube videos:

```
[M05 Topic Research] ──> [M06 Script Studio] ──> [M07 Voice Studio] ──> [M08 Visual Engine]
                                                                                │
                                                                                ▼
[M13 Analytics Feedback] <── [M12 YouTube Publishing] <── [M11 QA Veto Gate] <── [M09/M10 Video & Thumbnails]
```

By combining deterministic citation verification, multi-stage LLM reasoning (via Google Gemini 1.5 Flash/Pro), local neural text-to-speech (Edge-TTS), procedural FFmpeg 6.x multi-track video assembly, Pillow thumbnail composition, a 14-Point Pre-Publish QA Veto Gate, and official YouTube Data API v3 OAuth 2.0 resumable publishing, Creator Studio AI functions as a 24/7 autonomous production studio with zero manual video editing required.

---

## 🏗️ Monorepo Architecture

```
creator-studio-ai/
├── frontend/                   # Next.js 15.1.0 App Router, React 19, TypeScript 5.6.3, Tailwind CSS
│   ├── src/app/                # 28 routed views (Obsidian #090A0D + Vivid Ember #FF7A00 theme)
│   ├── src/components/         # AppShell, navigation, modals, stat cards, progress bars
│   └── src/lib/                # Unified API client (api.ts), auth session manager, Supabase SDK
├── backend/                    # FastAPI 0.115, Python 3.12, SQLAlchemy 2.0 Async, Pydantic v2
│   ├── app/api/v1/             # 23 modular REST routers with tenant isolation & RBAC
│   ├── app/core/               # Pydantic Settings, AES-256-GCM encryption, structured logging
│   ├── app/models/             # 52 SQLAlchemy declarative models across 10 functional domains
│   ├── app/providers/          # Google Gemini, Edge-TTS, Pexels, Pixabay, Local Mock Engine
│   ├── app/services/           # 28 domain services (queue, script, audio, video, QA, YouTube)
│   ├── app/workers/            # Autonomous queue runner with PostgreSQL FOR UPDATE SKIP LOCKED
│   └── alembic/                # 10 database migration revisions (0001 to 0010)
├── docs/                       # Complete product blueprints, runbooks, and specifications
│   ├── ARCHITECTURE.md         # System topology, queue model, and database design
│   ├── API_INTEGRATION.md      # Full REST API endpoint mapping table (23 routers)
│   ├── DATABASE_SETUP.md       # PostgreSQL connection, Alembic migrations & table schema
│   ├── ENVIRONMENT_SETUP.md    # Environment variable reference (.env.example)
│   ├── LOCAL_DEVELOPMENT.md    # Quickstart guide & Windows PowerShell commands
│   ├── SECURITY_CHECKLIST.md   # Zero-leakage audit, AES-256 tokens, spend governor
│   ├── TESTING.md              # 239 backend tests + frontend validation runbook
│   └── DEPLOYMENT.md           # Zero-cost staging deployment on GitHub Pages & Supabase
├── scripts/                    # Windows PowerShell developer automation scripts
│   ├── start-backend.ps1       # Launches FastAPI backend on port 8000
│   ├── start-worker.ps1        # Starts the persistent queue worker daemon
│   ├── stop-services.ps1       # Gracefully terminates local Python background processes
│   ├── test.ps1                # Full-stack test runner (pytest + frontend typecheck & lint)
│   └── dev.ps1                 # Concurrent frontend & backend development environment
├── storage/                    # Persistent local media working directory (git-ignored)
│   ├── audio/                  # Mastered WAV narration tracks (-14.0 LUFS)
│   ├── renders/                # Assembled 1080p MP4 master videos with burned typography
│   └── thumbnails/             # Exact 1280x720 Pillow-rendered thumbnail compositions
├── .env.example                # Root environment configuration template
└── README.md                   # This project manual
```

---

## 🛠️ Technology Stack & Zero-Cost Governance

| Subsystem | Technology | Operational Tier & Zero-Cost Strategy |
| :--- | :--- | :--- |
| **Frontend Framework** | **Next.js 15.1.0 + React 19** | Static HTML Export (`output: "export"`) deployed to GitHub Pages ($0.00). |
| **Design System** | **Tailwind CSS + Lucide Icons** | Bespoke Obsidian Dark canvas (`#090A0D`) with Vivid Ember accent (`#FF7A00`). |
| **Backend REST Gateway**| **FastAPI 0.115 (Python 3.12)** | Asynchronous high-concurrency API gateway running locally or containerized. |
| **Database & Queue** | **PostgreSQL 15 (Supabase Free)**| 52 tables, ACID transactions, atomic queue via `SELECT ... FOR UPDATE SKIP LOCKED`. |
| **AI Reasoning Engine** | **Google Gemini 1.5 Flash / Pro** | Google AI Studio free tier (15 RPM / 1,500 RPD) with token-bucket rate limiter. |
| **Neural Voice Engine** | **Microsoft Edge-TTS / Kokoro** | Zero-cost neural TTS producing 24kHz / 48kHz audio with word-level timestamps. |
| **Video Assembly** | **FFmpeg 6.x & ASS Typography** | Multi-track audio ducking, kinetic subtitles, pan/zoom motion effects. |
| **Thumbnail Engine** | **Pillow 10.x Procedural PIL** | Multi-layer contrast rendering generating 3 variants (A, B, C) per project. |
| **Spend Governor** | **In-Memory & DB Circuit Breaker**| Hard-locks monthly spending ceiling at `$0.00`; rejects all billable requests. |
| **Publishing Protocol** | **YouTube Data API v3** | Official resumable chunked upload protocol with AES-256-GCM encrypted tokens. |

---

## 🚦 Verified Test & Build Status

- **Backend Pytest Suite:** **239 / 239 PASSED (100%)** across 59 modules in 125.67s.
- **Frontend Type Safety:** **0 Errors** (`tsc --noEmit` verified clean).
- **Frontend Linter:** **0 Errors** (`next lint` verified clean).
- **Frontend Static Pages:** **28 / 28 Pre-Rendered** (`next build` output verified).
- **Database Migrations:** **10 / 10 Applied** (`alembic upgrade head` verified).
- **Disaster Recovery:** **RTO: 2.54 ms, RPO: 0.015s, 100% SHA match**.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.12+** in `backend/.venv`
- **Node.js 20+** and `npm`
- **PostgreSQL 15+** (Local or Supabase Free Tier)
- **FFmpeg & FFprobe** installed in system PATH

### 2. Environment Setup
```powershell
# Copy configuration templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

### 3. Launching Services (Windows PowerShell)
```powershell
# Start FastAPI backend server (Port 8000)
powershell -File .\scripts\start-backend.ps1

# Start durable queue worker daemon
powershell -File .\scripts\start-worker.ps1

# Start Next.js development server (Port 3000)
npm --prefix frontend run dev
```

### 4. Running the Complete Verification Suite
```powershell
powershell -File .\scripts\test.ps1
```

---

## 📖 Technical Documentation Sitemap

For in-depth operational and architectural specifications, consult the documents in `/docs`:
- [Architecture & Topology](docs/ARCHITECTURE.md)
- [API Endpoint Specification](docs/API_INTEGRATION.md)
- [Database Setup & Migrations](docs/DATABASE_SETUP.md)
- [Environment Configuration Reference](docs/ENVIRONMENT_SETUP.md)
- [Local Development Guide](docs/LOCAL_DEVELOPMENT.md)
- [Security Audit & Compliance Checklist](docs/SECURITY_CHECKLIST.md)
- [Testing & Quality Verification Strategy](docs/TESTING.md)
- [Staging & Production Deployment Guide](docs/DEPLOYMENT.md)

---

## 👤 Project Owner

**Muhammad Ali**  
Portfolio: [alibuild.site](https://alibuild.site)  
GitHub: [@alikhan14756](https://github.com/alikhan14756)  
Project Repository: [ai_auto](https://github.com/alikhan14756/ai_auto)
