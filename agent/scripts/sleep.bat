@echo off
cd /d C:\ai
echo.
echo Agent Sleep — Offline Processing
echo =================================
echo.
echo Make sure the agent session is closed before running this.
echo (The agent should have saved its state before you closed it.)
echo.
echo Phase 1: Memory Consolidation
echo   Reviewing working memory, promoting, pruning...
echo.
bash agent/scripts/consolidate.sh
echo.
echo Phase 2: Mycelial Network Consolidation
echo   Decaying unused connections, promoting scouts, pruning dead ends...
echo.
python agent/mycelial/consolidate.py sleep
echo.
echo Phase 3: Dream Processing
echo   Finding connections, surfacing questions, generating insights...
echo.
bash agent/scripts/dream.sh
echo.
echo ========================================
echo Sleep cycle complete. Safe to shut down.
echo.
echo To wake up later: run start.bat
echo.
pause
