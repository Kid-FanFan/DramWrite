# ScriptMaster - Start All Services
# Usage: .\start-all.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    ScriptMaster - Start All             " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = $PSScriptRoot

# Start backend
Write-Host "Starting backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$scriptDir\start-backend.ps1'"

# Wait for backend
Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$scriptDir\start-frontend.ps1'"

Write-Host ""
Write-Host "OK Services started in new windows" -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close PowerShell windows to stop services" -ForegroundColor Yellow
