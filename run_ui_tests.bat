@echo off
setlocal
echo ==============================================================================
echo ClassSync: Automated Visual UI Testing Suite (Playwright + Chrome)
echo Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
echo Availability Monitoring, and Conflict Detection System
echo ==============================================================================
echo.

echo [1/3] Checking environment and dependencies...
cd /d "%~dp0"

echo [2/3] Choose Test Execution Mode:
echo   1. Headed Mode (Opens real Chrome browser window and executes tests)
echo   2. Interactive Playwright UI Mode (Inspect DOM, DevTools, Time-Travel Steps)
echo   3. Headless Mode (Fast CLI execution with reporter)
echo.
set /p mode="Enter choice [1, 2, or 3] (default is 1): "

if "%mode%"=="2" (
    echo [3/3] Launching Playwright Interactive UI...
    call pnpm --filter web exec playwright test --ui
) else if "%mode%"=="3" (
    echo [3/3] Running Headless Suite...
    call pnpm --filter web exec playwright test
) else (
    echo [3/3] Launching Headed Chrome Browser Automation...
    call pnpm --filter web exec playwright test --headed
)

echo.
echo ==============================================================================
echo Tests execution complete.
echo ==============================================================================
pause
