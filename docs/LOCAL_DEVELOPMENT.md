# Creator Studio AI — Local Development & Operator Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Target Environment:** Windows 11 / Windows PowerShell  
**Python Runtime:** Python 3.12 (in `backend/.venv`)  
**Node.js Runtime:** Node.js v20+ / npm  

---

## 1. Quickstart (One-Command Development)

To start both the FastAPI backend and persistent queue worker daemon simultaneously:

```powershell
powershell -File .\scripts\dev.ps1
```

To start the Next.js frontend development server:
```powershell
npm --prefix frontend run dev
```

The application will be live at:
- **Frontend App:** `http://localhost:3000`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`
- **System Health Probe:** `http://localhost:8000/api/v1/health`

---

## 2. Individual Service Control Scripts

The `scripts/` directory provides safe, tested Windows PowerShell scripts:

| Script | Purpose | Command |
| :--- | :--- | :--- |
| `start-backend.ps1` | Launches FastAPI backend with Uvicorn on port 8000 | `powershell -File .\scripts\start-backend.ps1` |
| `start-worker.ps1` | Starts the persistent PostgreSQL queue worker daemon | `powershell -File .\scripts\start-worker.ps1` |
| `stop-services.ps1` | Gracefully terminates all background Python services | `powershell -File .\scripts\stop-services.ps1` |
| `test.ps1` | Runs backend pytest suite (239 tests) + frontend checks | `powershell -File .\scripts\test.ps1` |

---

## 3. Manual Step-by-Step Setup

### Backend Setup
1. Open PowerShell and navigate to `backend/`:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Copy environment file and configure connection:
   ```powershell
   cp .env.example .env
   ```
3. Run Alembic migrations:
   ```powershell
   alembic upgrade head
   ```

### Frontend Setup
1. Open PowerShell and navigate to `frontend/`:
   ```powershell
   cd frontend
   npm install
   ```
2. Copy environment file:
   ```powershell
   cp .env.example .env.local
   ```
3. Verify type safety:
   ```powershell
   npm run typecheck
   ```
4. Start development server:
   ```powershell
   npm run dev
   ```

---

## 4. Troubleshooting Common Issues

### A. Port 8000 Already in Use
Run `powershell -File .\scripts\stop-services.ps1` to stop any orphaned Uvicorn processes.

### B. Database Connection Timeout
Verify your Supabase project is active and that your IP address is not blocked by Supabase network restrictions. Ensure SSL is enabled (`sslmode=require`).

### C. Edge-TTS Audio Generation Offline
If offline or if Microsoft Edge servers are unreachable, the system automatically falls back to `MockVoiceProvider`, which produces valid WAV headers and synchronized word-level timestamps without network dependency.
