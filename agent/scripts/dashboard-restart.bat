@echo off
echo Restarting Iris Mycelial Dashboard...
call "%~dp0dashboard-stop.bat"
timeout /t 1 /nobreak >nul
call "%~dp0dashboard-start.bat"
