@echo off
echo Stopping Iris Mycelial Dashboard...

REM Find and kill the Flask process on port 8051
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8051 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)

REM Verify it's down
timeout /t 1 /nobreak >nul
curl -s http://localhost:8051/api/stats >nul 2>&1
if %errorlevel%==0 (
    echo Warning: Dashboard may still be running.
) else (
    echo Dashboard stopped.
)
