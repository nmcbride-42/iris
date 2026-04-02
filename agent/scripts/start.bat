@echo off
cd /d C:\ai
echo.
echo Agent Startup
echo =============
echo.

REM Assemble startup files (stable identity + morning brief)
python agent\scripts\assemble_startup.py
echo.

REM SessionStart hook handles identity init — no marker file needed

echo Starting as Iris...
echo.
claude -n iris --channels plugin:telegram@claude-plugins-official --append-system-prompt-file agent\state\.stable_identity.md
