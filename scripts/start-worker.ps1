# Creator Studio AI - Worker Startup Script
# Wrapper around start-staging-worker.ps1
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stagingScript = Join-Path $scriptDir "start-staging-worker.ps1"

if (Test-Path $stagingScript) {
    & $stagingScript @args
} else {
    Write-Host "[ERROR] Could not find $stagingScript" -ForegroundColor Red
    exit 1
}
