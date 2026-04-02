@echo off
echo Starting Iris Mycelial Dashboard...

REM Check if already running
curl -s http://localhost:8051/api/stats >nul 2>&1
if %errorlevel%==0 (
    echo Dashboard is already running at http://localhost:8051
    exit /b 0
)

cd /d C:\ai\agent\mycelial\dashboard
start /b "" python app.py >nul 2>&1

REM Wait for it to come up
timeout /t 3 /nobreak >nul
curl -s http://localhost:8051/api/stats >nul 2>&1
if %errorlevel%==0 (
    echo Dashboard running at http://localhost:8051
) else (
    echo Failed to start dashboard. Check python/flask installation.
)
