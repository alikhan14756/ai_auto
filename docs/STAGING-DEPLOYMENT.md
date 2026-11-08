# Creator Studio AI — Staging Deployment Guide

**Platform:** Creator Studio AI  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Document Status:** Production-Grade Staging Deployment Manual  
**Release Version:** `v0.1.0-RELEASE`  
**Date:** 2026-11-08  

---

## 1. Staging Architecture Overview

The staging topology mirrors the production architecture with strict process isolation, persistent database storage, durable background job workers, and Next.js frontend delivery:

```
                          [User Web Browser]
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  creator_studio_frontend     │
                   │  Next.js 15 (Port 3000)      │
                   └──────────────┬───────────────┘
                                  │
                         HTTP / REST API (8000)
                                  ▼
                   ┌──────────────────────────────┐
                   │  creator_studio_api          │
                   │  FastAPI Gateway (Port 8000) │
                   └───────┬──────────────┬───────┘
                           │              │
          SQLAlchemy Async │              │ Durable Queue Leases
          Transactions     │              │ (SKIP LOCKED)
                           ▼              ▼
     ┌────────────────────────┐  ┌─────────────────────────────────┐
     │  creator_studio_db     │  │  creator_studio_worker          │
     │  PostgreSQL 16 Alpine  │  │  Persistent Python 3.12 Daemon  │
     │  (Port 5432)           │  │  Video Compositor / Watchdog    │
     └────────────────────────┘  └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                     ┌─────────────────────────┐
                                     │  Shared Persistent Vol  │
                                     │  app_storage (/storage) │
                                     └─────────────────────────┘
```

---

## 2. Prerequisites & Host Requirements

- **Operating System:** Ubuntu 22.04+ LTS (Linux) or Windows 11 with WSL2 / PowerShell 7+.
- **Docker Engine:** Version 24.0+ and Docker Compose v2.20+.
- **Hardware Minimum:** 4 CPU cores, 8 GB RAM, 20 GB NVMe storage (for FFmpeg rendering buffers).
- **Network Ports:** `3000` (Frontend), `8000` (API Gateway), `5432` (PostgreSQL, internal to Docker network).

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Clone Repository and Configure Environment
```bash
git clone https://github.com/your-username/creator-studio-ai.git
cd creator-studio-ai

# Copy staging environment template
cp .env.example .env
```

Edit `.env` and verify the mandatory keys:
- `APP_ENV=staging`
- `APP_MASTER_ENCRYPTION_KEY`: 64-character hexadecimal key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `APP_SECRET_KEY`: Cryptographically secure random secret
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=your-secure-staging-password`
- `MAX_MONTHLY_SPEND_USD=0.00` (Enforces zero-dollar guardrail)

### Step 2: Build & Launch Multi-Container Stack
```bash
docker compose up -d --build
```

Verify all four containers are running and healthy:
```bash
docker compose ps
```
Expected output:
```
NAME                      IMAGE                      STATUS                   PORTS
creator_studio_db         postgres:16-alpine         Up (healthy)             0.0.0.0:5432->5432/tcp
creator_studio_api        creator-studio-ai-api      Up (healthy)             0.0.0.0:8000->8000/tcp
creator_studio_worker     creator-studio-ai-worker   Up                       
creator_studio_frontend   creator-studio-ai-frontend Up                       0.0.0.0:3000->3000/tcp
```

### Step 3: Run Database Migrations
Apply Alembic migrations from base to head on the PostgreSQL database:
```bash
docker compose exec api alembic upgrade head
```

### Step 4: Verify Deployment Health
Execute the health check probe:
```bash
curl -f http://localhost:8000/api/v1/health
```

Navigate in your web browser to:
- **Frontend Dashboard:** `http://localhost:3000`
- **Operational Health Center:** `http://localhost:3000/settings/health`
- **Interactive API Swagger Docs:** `http://localhost:8000/docs`

---

## 4. Alternative Local Staging (Without Docker)

For rapid local testing on Windows / macOS using native Python 3.12 and Node.js:

### 1. Database Setup
Ensure PostgreSQL is running locally on port 5432, or use local SQLite for quick checks.

### 2. Backend Gateway
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Persistent Worker Daemon
In a separate terminal:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.workers.runner
```

### 4. Frontend Application
In a third terminal:
```powershell
cd frontend
npm run dev -- --port 3000
```
