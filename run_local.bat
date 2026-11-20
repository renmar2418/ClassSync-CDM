@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo ClassSync: Local Development Stack Launcher
echo Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
echo Availability Monitoring, and Conflict Detection System
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [1/4] Ensuring database migrations and seed data...
python -m alembic upgrade head
python alembic/seed_data.py

echo.
echo [2/4] Starting ClassSync Microservices in Background...

start "ClassSync [Gateway :8000]" cmd /k "python -m uvicorn services.gateway.main:app --host 0.0.0.0 --port 8000 --reload"
start "ClassSync [Academic :8001]" cmd /k "python -m uvicorn services.academic.main:app --host 0.0.0.0 --port 8001 --reload"
start "ClassSync [Scheduling :8002]" cmd /k "python -m uvicorn services.scheduling.main:app --host 0.0.0.0 --port 8002 --reload"
start "ClassSync [Notification :8003]" cmd /k "python -m uvicorn services.notification.main:app --host 0.0.0.0 --port 8003 --reload"
start "ClassSync [Presence :8004]" cmd /k "python -m uvicorn services.presence.main:app --host 0.0.0.0 --port 8004 --reload"

echo.
echo [3/4] Starting Web Client (Vite PWA :5173)...
start "ClassSync [Web PWA :5173]" cmd /k "pnpm --filter web dev --port 5173 --host"

echo.
echo [4/4] Opening Web App in Browser...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo ==============================================================================
echo ClassSync local stack is running:
echo   - Web PWA:              http://localhost:5173
echo   - Gateway API Docs:     http://localhost:8000/docs
echo   - Academic Service:     http://localhost:8001/docs
echo   - Scheduling Service:   http://localhost:8002/docs
echo   - Notification Service: http://localhost:8003/docs
echo   - Presence Service:     http://localhost:8004/docs
echo ==============================================================================
echo Keep the service command windows open. Press any key to exit this launcher.
pause
