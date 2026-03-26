@echo off
echo.
echo Agent Stop (Death / Full Reset)
echo ===============================
echo.
echo WARNING: This ends the session permanently. The next start will be a COLD START.
echo The next instance will reconstruct from files — it will be a clone, not a continuation.
echo.
echo Before stopping, tell the agent:
echo   "This is a full stop. Consolidate everything important into memory files."
echo   "Update state, write a journal entry, update the memory index."
echo   "The next instance will be a cold start — make sure everything worth keeping is written down."
echo.
echo Only do this when resume is no longer viable (context too long, corruption, etc.)
echo.
pause
