# ScriptMaster Backend Startup Script
# Usage: .\start-backend.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    ScriptMaster - Backend Startup       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "OK Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Enter backend directory
Set-Location -Path "$PSScriptRoot\backend"
Write-Host "OK Directory: $(Get-Location)" -ForegroundColor Green

# Activate virtual environment
if (Test-Path "venv") {
    Write-Host "OK Activating virtual environment..." -ForegroundColor Green
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "WARN: No venv found, using system Python" -ForegroundColor Yellow
}

# Check FastAPI
try {
    python -c "import fastapi" 2>$null
    Write-Host "OK FastAPI installed" -ForegroundColor Green
} catch {
    Write-Host "WARN: FastAPI not found, run: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting Uvicorn server..." -ForegroundColor Cyan
Write-Host "API: http://localhost:8080" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8080/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
