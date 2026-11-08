# Creator Studio AI — Production Deployment Guide

**Target Audience:** DevOps Engineers, Platform Administrators, Site Reliability Engineers  
**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening & Official Release  
**Release Version:** v0.1.0-RELEASE  

---

## 1. Hosting Architecture Overview

The production deployment topology separates concerns into decoupled, independently scalable components:

1. **Frontend:** Deployed to **Vercel** or any Edge Next.js hosting platform (or self-hosted via Docker).
2. **Backend API Gateway:** Containerized FastAPI app deployed to a persistent host (Docker / Railway / Render / Ubuntu VPS).
3. **Background Worker Daemon:** Persistent worker process running with FFmpeg 7.x on the host. Long-running video compositing must never run on serverless functions.
4. **Database:** Managed **Supabase PostgreSQL 16** with automated daily point-in-time backups.
5. **Asset Storage:** Cloudflare R2 (S3-compatible, zero egress fees) or persistent NVMe volume for video clips, audio WAVs, and thumbnails.

```
       [Users / Web Browsers]
                 │
                 ▼
     [Vercel: Next.js 15 Frontend]
                 │
                 │ HTTPS (Bearer JWT)
                 ▼
  [Persistent Host: FastAPI API Gateway] ◄───► [Supabase PostgreSQL 16]
                 ▲                                     ▲
                 │ IPC / Queue                         │
                 ▼                                     │
  [Persistent Host: Worker Daemon (FFmpeg)] ───────────┘
                 │
                 ▼
        [Cloudflare R2 Storage]
```

---

## 2. Docker Multi-Container Deployment

### Prerequisites
- Docker Engine 24.x+ and Docker Compose 2.20+
- Public domain with SSL certificate (Let's Encrypt / Cloudflare)
- Supabase PostgreSQL instance URL or local PostgreSQL 16 container

### Multi-Service Docker Compose Topology
In production, the backend API gateway and worker daemon run in separate containers sharing access to storage and database:

```yaml
version: "3.8"

services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - APP_MASTER_ENCRYPTION_KEY=${APP_MASTER_ENCRYPTION_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - STORAGE_DRIVER=local
      - LOCAL_STORAGE_DIR=/data/media
    volumes:
      - media_storage:/data/media
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m app.workers.job_worker
    environment:
      - APP_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - APP_MASTER_ENCRYPTION_KEY=${APP_MASTER_ENCRYPTION_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - STORAGE_DRIVER=local
      - LOCAL_STORAGE_DIR=/data/media
    volumes:
      - media_storage:/data/media
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
      - NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
    restart: unless-stopped

volumes:
  media_storage:
    driver: local
```

---

## 3. Step-by-Step Production Deployment

1. **Clone repository and setup environment:**
   ```bash
   git clone https://github.com/muhammad-ali/creator-studio-ai.git
   cd creator-studio-ai
   cp .env.example .env
   # Edit .env with production credentials (DATABASE_URL, APP_SECRET_KEY, etc.)
   ```

2. **Generate secure production encryption keys:**
   ```bash
   # Generate 64-character master encryption hex key (AES-256-GCM)
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Run database migrations:**
   ```bash
   cd backend
   alembic upgrade head
   cd ..
   ```

4. **Start containerized stack:**
   ```bash
   docker compose up -d --build
   ```

5. **Verify service health:**
   ```bash
   curl -f http://localhost:8000/api/v1/health
   # Expected: {"status":"healthy","database":"connected","queue_workers":"active"}
   ```

---

## 4. Frontend Deployment (Vercel)

1. Connect the GitHub repository to Vercel.
2. Set **Root Directory** to `frontend`.
3. Configure Environment Variables in Vercel Project Settings:
   - `NEXT_PUBLIC_API_URL`: `https://api.yourdomain.com/api/v1`
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://your-project.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `<your-supabase-anon-key>`
4. Deploy branch `master` or `main`. Next.js builds all 28 pages statically and generates the edge-ready bundle.

---

## 5. Reverse Proxy & SSL Configuration (Nginx Example)

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE Streaming support for live job progress
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

---

## 6. Windows Local Development Setup

For local development on Windows:
```powershell
# In root directory:
powershell -File .\scripts\dev.ps1
```
This launches:
- Backend FastAPI server on `http://127.0.0.1:8000` with hot reload.
- Background worker polling daemon in a dedicated session.
- Frontend Next.js development server on `http://localhost:3000`.

To run tests:
```powershell
powershell -File .\scripts\test.ps1
```

---

## 7. Health Check Probes & Monitoring

The system exposes standard Kubernetes / cloud health endpoints:
- **Liveness Probe:** `GET /health` — Verifies process uptime and core dependencies.
- **Readiness Probe:** `GET /ready` — Verifies database connection and encryption keys.
- **Operational Health:** `GET /api/v1/system/production-health` — Real-time telemetry, active workflows, stalled stages, and watchdog status.
- **Admin Dashboard:** `https://yourdomain.com/settings/health` — Dedicated visual control panel for administrators.
