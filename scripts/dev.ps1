# Creator Studio AI - Development Server Runner (Windows PowerShell)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Starting Dev Environment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "..\backend"
$frontendPath = Join-Path $PSScriptRoot "..\frontend"

Write-Host "Starting Backend FastAPI on http://localhost:8000..." -ForegroundColor Yellow
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; .\.venv\Scripts\activate; uvicorn app.main:app --reload --port 8000" -PassThru

Write-Host "Starting Frontend Next.js on http://localhost:3000..." -ForegroundColor Yellow
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev" -PassThru

Write-Host "`nServices launched in separate PowerShell windows:" -ForegroundColor Green
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C or close windows to stop servers." -ForegroundColor Gray
