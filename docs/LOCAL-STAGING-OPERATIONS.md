# Creator Studio AI — Local Staging Operations Manual (Windows)

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Host Operating System:** Microsoft Windows  
**Hosting Model:** Zero-Cost Local-First Staging  
**Status:** Operational Runbook  

---

## 1. Quick Start Operations Guide

Creator Studio AI provides dedicated PowerShell automation scripts in the [`scripts/`](file:///d:/auto/ai%20automation/scripts/) directory to control the local staging environment.

```
========================================================================================
                      CREATOR STUDIO AI - STAGING CLI SHORTCUTS
========================================================================================
 Start Local Backend API   : powershell -File .\scripts\start-staging-backend.ps1
 Stop Local Backend API    : powershell -File .\scripts\stop-staging-backend.ps1
 Start Persistent Worker   : powershell -File .\scripts\start-staging-worker.ps1
 Stop Persistent Worker    : powershell -File .\scripts\stop-staging-worker.ps1
 Master Test Suite Runner  : powershell -File .\scripts\test.ps1
========================================================================================
```

---

## 2. Starting and Monitoring the Services

### Step 1: Start the FastAPI Backend
```powershell
powershell -File .\scripts\start-staging-backend.ps1
```
**What this script performs:**
1. Validates the Python 3.12 virtual environment at `backend/.venv`.
2. Verifies environment configuration in `.env` without printing secret values.
3. Checks for and verifies Supabase PostgreSQL database connectivity.
4. Executes Alembic schema check (`alembic upgrade head`).
5. Launches Uvicorn server on `http://127.0.0.1:8000` with logging to `storage/staging-backend.log`.
6. Saves process PID in `storage/staging-backend.pid`.
7. Polls `http://127.0.0.1:8000/health` until HTTP 200 OK is confirmed.

### Step 2: Start the Persistent Queue Worker Daemon
```powershell
powershell -File .\scripts\start-staging-worker.ps1
```
**What this script performs:**
1. Validates Python virtual environment.
2. Checks that an existing worker daemon is not already running.
3. Launches `python -m app.workers.runner` in background mode with output redirected to `storage/staging-worker.log`.
4. Saves process PID in `storage/staging-worker.pid`.
5. The worker establishes durable PostgreSQL task leases with `FOR UPDATE SKIP LOCKED` and broadcasts heartbeats every 10 seconds.
6. The worker process continues running autonomously even if the browser or frontend is closed.

### Step 3: Verifying Operational Health
- **Live Health Endpoint:** `http://127.0.0.1:8000/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Settings Health Dashboard:** Open `http://localhost:3000/settings/health` or the GitHub Pages URL.

---

## 3. Stopping the Staging Services

### Stop the Backend
```powershell
powershell -File .\scripts\stop-staging-backend.ps1
```
Reads `storage/staging-backend.pid`, sends termination signal to the process, removes the PID file, and ensures port 8000 is clean.

### Stop the Worker Daemon
```powershell
powershell -File .\scripts\stop-staging-worker.ps1
```
Reads `storage/staging-worker.pid`, signals the worker daemon to complete its current step and shut down cleanly, and deletes the PID file.

---

## 4. Media Storage & Directory Management

To protect local workstation disk space and maintain tenant security:

```
storage/
├── audio/          # Generated voiceover narration WAV files
├── captures/       # Video screenshots and visual storyboard crops
├── renders/        # Assembled MP4 video files
├── thumbnails/     # Composed JPG/PNG YouTube thumbnails
├── subtitles/      # Generated ASS/SRT caption files
├── staging-backend.log
├── staging-worker.log
├── staging-backend.pid
└── staging-worker.pid
```

### Storage Protection Rules:
1. **Tenant Path Isolation:** All file operations enforce tenant-scoped paths (`storage/{category}/{channel_id}/{project_id}/`).
2. **Path Traversal Shield:** File paths are resolved and validated using `os.path.commonpath` to prevent `../` directory escape attacks.
3. **Upload Size Validation:** Audio files capped at 50 MB; video assets capped at 500 MB; thumbnail images capped at 2 MB.
4. **Local Retention Cleanup:** Temporary chunk files in `storage/scratch` are deleted immediately upon render completion.

---

## 5. FFmpeg Installation & Resource Management

### Windows FFmpeg Setup
FFmpeg is required for real video rendering and audio mastering. If FFmpeg is not detected in your Windows PATH, Creator Studio AI automatically operates in **Deterministic Mock Rendering Mode** without crashing.

To enable real video compositing on Windows:
```powershell
# Install FFmpeg via Windows Package Manager
winget install Gyan.FFmpeg

# Or via Chocolatey
choco install ffmpeg

# Verify installation in a new PowerShell window:
ffmpeg -version
ffprobe -version
```

### Resource Protection on Windows Laptops:
- **Single Render Concurrency:** The background worker enforces a strict ceiling of **1 concurrent render job** to protect host CPU and RAM.
- **Memory Conservation:** Video rendering utilizes streaming FFmpeg pipes rather than loading uncompressed frames into RAM.
- **Rendering Timeout:** Renders timeout after 600 seconds (10 minutes), preventing runaway processes.
- **Resolution Preset:** Staging default is 1080p 30fps (`1920x1080`), avoiding 4K rendering overhead.

---

## 6. Connecting GitHub Pages to the Local Backend

When the frontend is hosted on **GitHub Pages** (`https://<owner>.github.io/<repo>/`) and the backend is running locally on your workstation, the browser needs to reach your API.

### Option A: Local Testing in Browser (Recommended Baseline)
Run the browser on the same Windows workstation where the backend is hosted. Configure the frontend with:
```bash
NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
```
Because browser requests originate from your local machine, the browser connects directly to `127.0.0.1:8000`.

### Option B: Cloudflare Tunnel (Zero-Cost Secure Public Endpoint)
If you wish to test the GitHub Pages deployment from mobile or external devices without exposing your home IP:

1. **Install Cloudflare Tunnel CLI:**
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. **Start Ephemeral Secure Tunnel:**
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8000
   ```
   *Cloudflare outputs a unique HTTPS URL (e.g. `https://random-name.trycloudflare.com`).*
3. **Configure Backend CORS:**
   Add the tunnel URL to `ALLOWED_ORIGINS` in `.env`:
   ```bash
   ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,https://<your-username>.github.io,https://random-name.trycloudflare.com"
   ```
4. **Update Frontend API Base URL:**
   Set `NEXT_PUBLIC_API_BASE_URL="https://random-name.trycloudflare.com"`.
5. **Terminating the Tunnel:**
   Simply press `Ctrl+C` in the cloudflared console. Your backend is immediately closed to the public.
