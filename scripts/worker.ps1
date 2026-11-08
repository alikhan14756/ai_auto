# Creator Studio AI - Background Worker Daemon Runner (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Background Worker Daemon" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "..\backend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Python virtual environment not found at $pythonPath. Run .\scripts\install.ps1 first." -ForegroundColor Red
    exit 1
}

Set-Location -Path $backendPath
$env:PYTHONPATH = "backend"

Write-Host "`nStarting autonomous worker daemon loop..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the worker daemon.`n" -ForegroundColor Yellow

try {
    & $pythonPath -m app.workers.runner
}
catch {
    Write-Host "`nWorker process stopped." -ForegroundColor Yellow
}
finally {
    Set-Location -Path "$PSScriptRoot\.."
}
