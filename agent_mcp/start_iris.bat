@echo off
echo.
echo Starting Iris — Autonomous Agent Loop
echo =======================================
echo.
echo Prerequisites:
echo   1. LM Studio server running on localhost:1234
echo   2. Unity Play mode started after this script
echo.
cd /d C:\ai\agent_mcp
"C:\Users\Nick\AppData\Local\Programs\Python\Python310\python.exe" autonomous_loop.py
pause
