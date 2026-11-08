# Creator Studio AI - Backend Startup Script
# Wrapper around start-staging-backend.ps1
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stagingScript = Join-Path $scriptDir "start-staging-backend.ps1"

if (Test-Path $stagingScript) {
    & $stagingScript @args
} else {
    Write-Host "[ERROR] Could not find $stagingScript" -ForegroundColor Red
    exit 1
}
