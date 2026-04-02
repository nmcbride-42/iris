@echo off
cd /d C:\ai
echo.
echo Agent Startup
echo =============
echo.

REM Assemble startup files (stable identity + morning brief)
python agent\scripts\assemble_startup.py
echo.

REM Drop startup marker so the identity-check hook fires on first response
echo startup > agent\state\.identity_check

echo Starting as Iris...
echo.
claude -n iris --channels plugin:telegram@claude-plugins-official --append-system-prompt-file agent\state\.stable_identity.md
