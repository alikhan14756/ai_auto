# Creator Studio AI - Automated Test Runner (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Running Test Suites" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Backend tests
Write-Host "`n[1/2] Running Backend Tests (pytest)..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "..\backend"
Set-Location -Path $backendPath
& ".\.venv\Scripts\pytest.exe" -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Backend tests passed successfully!" -ForegroundColor Green

# 2. Frontend typecheck and lint
Write-Host "`n[2/2] Running Frontend Checks (typecheck & lint)..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "..\frontend"
Set-Location -Path $frontendPath
npm run typecheck
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend typecheck failed!" -ForegroundColor Red
    exit 1
}
npm run lint
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend lint failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Frontend checks passed successfully!" -ForegroundColor Green

Set-Location -Path "$PSScriptRoot\.."
Write-Host "`nAll test suites passed!" -ForegroundColor Green
