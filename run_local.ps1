<#
.SYNOPSIS
    Starts the complete ClassSync local microservices and Web PWA stack.
.DESCRIPTION
    Runs database migrations, starts Uvicorn instances on ports 8000-8004,
    spins up Vite on port 5173, and launches the default browser.
#>

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "ClassSync: Local Development Stack Launcher (PowerShell)" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

Write-Host "[1/4] Ensuring database migrations and seed data..." -ForegroundColor Green
python -m alembic upgrade head
python alembic/seed_data.py

Write-Host "`n[2/4] Starting Microservices on Ports 8000-8004..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn services.gateway.main:app --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn services.academic.main:app --port 8001 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn services.scheduling.main:app --port 8002 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn services.notification.main:app --port 8003 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn services.presence.main:app --port 8004 --reload"

Write-Host "`n[3/4] Starting Web Client (Vite PWA :5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "pnpm --filter web dev --port 5173 --host"

Write-Host "`n[4/4] Opening Web App in Browser..." -ForegroundColor Green
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "ClassSync stack active: http://localhost:5173 (Gateway API: http://localhost:8000/docs)" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
