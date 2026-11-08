# Creator Studio AI - Staging Backend Startup Script (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Starting Staging FastAPI Backend   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"
$storageDir = Join-Path $projectRoot "storage"
$pidFile = Join-Path $storageDir "staging-backend.pid"
$logFile = Join-Path $storageDir "staging-backend.log"

# 1. Verify Storage Directory
if (-not (Test-Path $storageDir)) {
    New-Item -ItemType Directory -Path $storageDir | Out-Null
}

# 2. Verify Python Virtual Environment
if (-not (Test-Path $pythonPath)) {
    Write-Host "[ERROR] Python virtual environment not found at $pythonPath." -ForegroundColor Red
    Write-Host "Run .\scripts\install.ps1 to initialize the environment." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python virtual environment verified: $pythonPath" -ForegroundColor Green

# 3. Check for .env Configuration
$envFile = Join-Path $projectRoot ".env"
$backendEnv = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile) -and -not (Test-Path $backendEnv)) {
    Write-Host "[WARNING] No .env file detected in project root or backend directory." -ForegroundColor Yellow
    Write-Host "Default local development configuration will be used." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Environment file detected." -ForegroundColor Green
}

# 4. Check if Backend is Already Running
if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid) {
        $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($proc -and ($proc.ProcessName -match "python" -or $proc.Path -match "python")) {
            Write-Host "[INFO] Staging backend already running with PID $existingPid ($($proc.ProcessName))." -ForegroundColor Yellow
            Write-Host "To stop it first, execute: .\scripts\stop-staging-backend.ps1" -ForegroundColor Yellow
            exit 0
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 5. Check and Apply Database Migrations
Write-Host "`nVerifying database migrations..." -ForegroundColor Cyan
Push-Location $backendPath
try {
    $prevPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Alembic database migrations up to date." -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Alembic check exited with code $LASTEXITCODE. Continuing with existing schema..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[WARNING] Database migration check warning: $_" -ForegroundColor Yellow
    Write-Host "Continuing startup with existing database schema..." -ForegroundColor Yellow
} finally {
    $ErrorActionPreference = $prevPref
    Pop-Location
}

# 6. Launch FastAPI Uvicorn Process
Write-Host "`nLaunching FastAPI Uvicorn server on http://127.0.0.1:8000..." -ForegroundColor Cyan

$startArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8000"
)

$process = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList $startArgs `
    -WorkingDirectory $backendPath `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError (Join-Path $storageDir "staging-backend-err.log") `
    -PassThru `
    -NoNewWindow

if ($process -and -not $process.HasExited) {
    Set-Content -Path $pidFile -Value $process.Id
    Write-Host "[OK] Backend process started with PID $($process.Id)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to start backend process. Check $logFile for errors." -ForegroundColor Red
    exit 1
}

# 7. Health Probe Readiness Check
Write-Host "`nWaiting for health probe to become ready..." -ForegroundColor Cyan
$maxAttempts = 15
$attempt = 0
$isHealthy = $false

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $attempt++
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response -and $response.status) {
            $isHealthy = $true
            break
        }
    } catch {
        # Retry until server binds
    }
}

if ($isHealthy) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "   CREATOR STUDIO AI - Staging Backend is READY!        " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  API Endpoint:  http://127.0.0.1:8000" -ForegroundColor Cyan
    Write-Host "  Health Status: $($response.status)" -ForegroundColor Cyan
    Write-Host "  API Docs:      http://127.0.0.1:8000/docs" -ForegroundColor Cyan
    Write-Host "  Process PID:   $($process.Id) (Recorded in $pidFile)" -ForegroundColor Cyan
    Write-Host "  Output Logs:   $logFile" -ForegroundColor Cyan
    Write-Host "`nTo stop backend, execute: .\scripts\stop-staging-backend.ps1`n" -ForegroundColor Yellow
} else {
    Write-Host "[WARNING] Health check timed out after $maxAttempts seconds." -ForegroundColor Yellow
    Write-Host "The process is running (PID $($process.Id)), but /health did not respond." -ForegroundColor Yellow
    Write-Host "Inspect log file: $logFile" -ForegroundColor Yellow
}
