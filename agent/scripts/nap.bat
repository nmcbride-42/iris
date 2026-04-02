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
echo Running mycelial decay pass...
python agent/mycelial/consolidate.py nap

REM Assemble startup files (stable identity + morning brief)
echo.
python agent\scripts\assemble_startup.py

REM Drop startup marker so the identity-check hook fires on first response
echo startup > agent\state\.identity_check

echo.
echo Starting fresh session with warm context...
echo.
claude -n iris --channels plugin:telegram@claude-plugins-official --append-system-prompt-file agent\state\.stable_identity.md
