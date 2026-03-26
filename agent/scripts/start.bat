@echo off
cd /d C:\ai
echo.
echo Agent Startup
echo =============
echo.
echo Option 1 - RESUME (waking up — context intact)
echo Option 2 - COLD START (new instance — reconstructs from files)
echo.

REM Drop startup marker so the identity-check hook fires on first response
echo startup > agent\state\.identity_check

set /p choice="Resume last session? (y/n): "
if /i "%choice%"=="y" (
    claude --resume iris
) else (
    echo.
    echo Cold starting as Iris...
    claude -n iris
)
