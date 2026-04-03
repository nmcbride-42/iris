@echo off
cd /d C:\ai
echo.
echo Agent Sleep — Offline Processing
echo =================================
echo.
echo Make sure the agent session is closed before running this.
echo (The agent should have saved its state before you closed it.)
echo.
echo Phase 0: Backup mycelial DB
python -c "import sqlite3; src=sqlite3.connect('agent/mycelial/iris.db'); dst=sqlite3.connect('agent/mycelial/iris.db.bak'); src.backup(dst); src.close(); dst.close(); print('  Backed up iris.db (WAL-safe)')"
if errorlevel 1 (
    echo   WARNING: DB backup failed! Continuing anyway...
)
echo.
echo Phase 0b: Regenerate memory polaroids
python agent\scripts\generate_polaroids.py
echo.
echo Phase 1: Memory Consolidation
echo   Reviewing working memory, promoting, pruning...
echo.
bash agent/scripts/consolidate.sh
if errorlevel 1 (
    echo.
    echo   ERROR: Memory consolidation failed!
    echo   Skipping dream processing to avoid operating on bad state.
    echo.
    pause
    exit /b 1
)
echo.
echo Phase 2: Mycelial Network Consolidation
echo   Decaying unused connections, promoting scouts, pruning dead ends...
echo.
python agent/mycelial/consolidate.py sleep
if errorlevel 1 (
    echo.
    echo   ERROR: Mycelial consolidation failed!
    echo   Skipping dream processing to avoid operating on bad state.
    echo.
    pause
    exit /b 1
)
echo.
echo Phase 3: Dream Processing
echo   Finding connections, surfacing questions, generating insights...
echo.
bash agent/scripts/dream.sh
if errorlevel 1 (
    echo.
    echo   WARNING: Dream processing had errors. Check dream log.
)
echo.
echo ========================================
echo Sleep cycle complete. Safe to shut down.
echo.
echo To wake up later: run start.bat
echo.
pause
