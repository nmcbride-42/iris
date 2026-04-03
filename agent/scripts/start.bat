@echo off
cd /d C:\ai
echo.
echo Agent Startup
echo =============
echo.

REM Assemble startup files (stable identity + morning brief)
python agent\scripts\assemble_startup.py
if errorlevel 1 (
    echo.
    echo ERROR: Startup assembly failed!
    echo Check that identity files exist in agent\identity\
    echo.
    pause
    exit /b 1
)

REM Verify critical files exist
if not exist agent\state\.stable_identity.md (
    echo ERROR: .stable_identity.md not generated!
    pause
    exit /b 1
)
echo.

REM SessionStart hook handles identity init — no marker file needed

echo Starting as Iris...
echo.
claude -n iris --channels plugin:telegram@claude-plugins-official --append-system-prompt-file agent\state\.stable_identity.md
