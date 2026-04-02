@echo off
echo Iris Mycelial Dashboard Status
echo ===============================
echo.

REM Check dashboard
curl -s http://localhost:8051/api/stats >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Dashboard running at http://localhost:8051
) else (
    echo [!!] Dashboard is NOT running
)

REM Check hook file exists
if exist "C:\ai\.claude\hooks\mycelial-hook.sh" (
    echo [OK] Hook script exists
) else (
    echo [!!] Hook script missing
)

REM Check tracking file
if exist "C:\ai\agent\mycelial\.last_processed" (
    echo [OK] Hook tracking file exists
) else (
    echo [--] No tracking file yet (hook hasn't fired)
)

echo.
echo --- Network Stats ---
python "%~dp0dashboard-status-helper.py"
echo.
