# Creator Studio AI - Automated Setup Script (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CREATOR STUDIO AI - Environment Installation" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python runtime
Write-Host "`n[1/4] Checking Python runtime..." -ForegroundColor Yellow
$pyVersion = python --version
Write-Host "Found: $pyVersion" -ForegroundColor Green

# 2. Check Node runtime
Write-Host "`n[2/4] Checking Node & npm runtime..." -ForegroundColor Yellow
$nodeVersion = node -v
$npmVersion = npm -v
Write-Host "Found Node: $nodeVersion | npm: $npmVersion" -ForegroundColor Green

# 3. Backend Virtual Environment & Dependencies
Write-Host "`n[3/4] Setting up Python virtual environment in backend/.venv..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\..\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created backend\.venv" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists in backend\.venv" -ForegroundColor Gray
}

Write-Host "Upgrading pip and installing backend dependencies..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Write-Host "Backend dependencies installed successfully." -ForegroundColor Green

# 4. Frontend Dependencies
Write-Host "`n[4/4] Installing frontend dependencies in frontend/..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\..\frontend"
npm install
Write-Host "Frontend dependencies installed successfully." -ForegroundColor Green

Set-Location -Path "$PSScriptRoot\.."

# 5. Environment configuration notice
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "`nCreated local .env from .env.example. Please review and populate your keys." -ForegroundColor Magenta
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Installation complete! You can now run:" -ForegroundColor Green
Write-Host "   .\scripts\dev.ps1    (Start development servers)" -ForegroundColor White
Write-Host "   .\scripts\test.ps1   (Run test suites)" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
