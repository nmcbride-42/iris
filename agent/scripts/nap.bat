@echo off
cd /d C:\ai
echo.
echo Agent Nap — Quick Consolidation
echo ================================
echo.
echo Before running this, make sure Iris has written her warm-start state.
echo (She should have updated agent/state/warmstart.md and current.md)
echo.
echo Unlike sleep, a nap skips dreaming and deep consolidation.
echo It does run a light mycelial decay pass.
echo.
pause
echo.

REM Brief quiesce — let dying async hooks finish writing to the DB
echo Waiting for hooks to settle...
timeout /t 3 /nobreak >nul

echo Running mycelial decay pass...
python agent/mycelial/consolidate.py nap
if errorlevel 1 (
    echo   WARNING: Consolidation had errors. Continuing anyway...
)

REM Assemble startup files (stable identity + morning brief)
echo.
python agent\scripts\assemble_startup.py
if errorlevel 1 (
    echo   ERROR: Startup assembly failed!
    pause
    exit /b 1
)

REM SessionStart hook handles identity init — no marker file needed

echo.
echo Starting fresh session with warm context...
echo.
claude -n iris --channels plugin:telegram@claude-plugins-official --append-system-prompt-file agent\state\.stable_identity.md
