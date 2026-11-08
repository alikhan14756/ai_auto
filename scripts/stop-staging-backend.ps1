# Creator Studio AI - Staging Backend Shutdown Script (Windows PowerShell)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Stopping Staging FastAPI Backend   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$storageDir = Join-Path $projectRoot "storage"
$pidFile = Join-Path $storageDir "staging-backend.pid"

$stopped = $false

if (Test-Path $pidFile) {
    $targetPid = Get-Content $pidFile
    if ($targetPid) {
        Write-Host "Found recorded PID: $targetPid" -ForegroundColor Yellow
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($proc -and ($proc.ProcessName -match "python" -or $proc.Path -match "python")) {
            Write-Host "Sending termination signal to PID $targetPid ($($proc.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            $stopped = $true
            Write-Host "[OK] Stopped backend process (PID $targetPid)." -ForegroundColor Green
        } else {
            Write-Host "[INFO] Recorded PID $targetPid is either stale or not a Python process." -ForegroundColor Gray
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# Secondary cleanup check: find any lingering uvicorn processes listening on port 8000
$portCheck = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portCheck) {
    foreach ($conn in $portCheck) {
        $pId = $conn.OwningProcess
        Write-Host "Found lingering process on port 8000 (PID $pId). Stopping..." -ForegroundColor Yellow
        Stop-Process -Id $pId -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
}

if ($stopped) {
    Write-Host "`n[OK] Staging FastAPI backend successfully stopped.`n" -ForegroundColor Green
} else {
    Write-Host "`n[INFO] No active staging backend processes found on port 8000.`n" -ForegroundColor Gray
}
