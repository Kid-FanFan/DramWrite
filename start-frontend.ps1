# ScriptMaster Frontend Startup Script
# Usage: .\start-frontend.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    ScriptMaster - Frontend Startup      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "OK Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Node.js not found" -ForegroundColor Red
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version 2>&1
    Write-Host "OK npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: npm not found" -ForegroundColor Red
    exit 1
}

# Enter frontend directory
Set-Location -Path "$PSScriptRoot\frontend"
Write-Host "OK Directory: $(Get-Location)" -ForegroundColor Green

# Check node_modules
if (Test-Path "node_modules") {
    Write-Host "OK node_modules exists" -ForegroundColor Green
} else {
    Write-Host "WARN: node_modules not found, run: npm install" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting Vite dev server..." -ForegroundColor Cyan
Write-Host "URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

npm run dev
