# Creator Studio AI - Staging Worker Shutdown Script (Windows PowerShell)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Stopping Background Worker Daemon  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$storageDir = Join-Path $projectRoot "storage"
$pidFile = Join-Path $storageDir "staging-worker.pid"

$stopped = $false

if (Test-Path $pidFile) {
    $targetPid = Get-Content $pidFile
    if ($targetPid) {
        Write-Host "Found recorded Worker PID: $targetPid" -ForegroundColor Yellow
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($proc -and ($proc.ProcessName -match "python" -or $proc.Path -match "python")) {
            Write-Host "Signaling worker PID $targetPid ($($proc.ProcessName)) to complete current step and exit..." -ForegroundColor Yellow
            
            # Send soft close / kill without -Force
            Stop-Process -Id $targetPid -ErrorAction SilentlyContinue
            
            $timeoutSec = 5
            $timer = [System.Diagnostics.Stopwatch]::StartNew()
            while ($timer.Elapsed.TotalSeconds -lt $timeoutSec) {
                if (-not (Get-Process -Id $targetPid -ErrorAction SilentlyContinue)) {
                    break
                }
                Start-Sleep -Milliseconds 500
            }
            
            if (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {
                Write-Host "Worker did not exit within ${timeoutSec}s. Terminating forcefully..." -ForegroundColor Yellow
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }

            $stopped = $true
            Write-Host "[OK] Stopped worker process (PID $targetPid)." -ForegroundColor Green
        } else {
            Write-Host "[INFO] Recorded Worker PID $targetPid is either stale or not a Python process." -ForegroundColor Gray
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

if ($stopped) {
    Write-Host "`n[OK] Background worker daemon successfully stopped.`n" -ForegroundColor Green
} else {
    Write-Host "`n[INFO] No active background worker process found.`n" -ForegroundColor Gray
}
