# Creator Studio AI - Staging Worker Startup Script (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Starting Background Worker Daemon  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"
$storageDir = Join-Path $projectRoot "storage"
$pidFile = Join-Path $storageDir "staging-worker.pid"
$logFile = Join-Path $storageDir "staging-worker.log"

# 1. Verify Storage Directory
if (-not (Test-Path $storageDir)) {
    New-Item -ItemType Directory -Path $storageDir | Out-Null
}

# 2. Verify Python Virtual Environment
if (-not (Test-Path $pythonPath)) {
    Write-Host "[ERROR] Python virtual environment not found at $pythonPath." -ForegroundColor Red
    Write-Host "Run .\scripts\install.ps1 first." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python virtual environment verified: $pythonPath" -ForegroundColor Green

# 3. Check if Worker Daemon is Already Running
if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid) {
        $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($proc -and ($proc.ProcessName -match "python" -or $proc.Path -match "python")) {
            Write-Host "[INFO] Staging worker daemon already running with PID $existingPid ($($proc.ProcessName))." -ForegroundColor Yellow
            Write-Host "To stop it first, execute: .\scripts\stop-staging-worker.ps1" -ForegroundColor Yellow
            exit 0
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 4. Launch Background Worker Daemon
Write-Host "`nLaunching autonomous worker daemon (app.workers.runner)..." -ForegroundColor Cyan

$process = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList "-m", "app.workers.runner" `
    -WorkingDirectory $backendPath `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError (Join-Path $storageDir "staging-worker-err.log") `
    -PassThru `
    -NoNewWindow

if ($process -and -not $process.HasExited) {
    Set-Content -Path $pidFile -Value $process.Id
    Start-Sleep -Seconds 1
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "   CREATOR STUDIO AI - Worker Daemon is RUNNING!          " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Process PID:   $($process.Id) (Recorded in $pidFile)" -ForegroundColor Cyan
    Write-Host "  Queue Engine:  PostgreSQL SKIP LOCKED Durable Leases" -ForegroundColor Cyan
    Write-Host "  Heartbeats:    Periodic 10s lease renewals" -ForegroundColor Cyan
    Write-Host "  Output Logs:   $logFile" -ForegroundColor Cyan
    Write-Host "`nThe worker daemon runs independently of the browser and frontend." -ForegroundColor Yellow
    Write-Host "To stop worker, execute: .\scripts\stop-staging-worker.ps1`n" -ForegroundColor Yellow
} else {
    Write-Host "[ERROR] Failed to start worker process. Check $logFile for errors." -ForegroundColor Red
    exit 1
}
