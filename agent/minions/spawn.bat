@echo off
setlocal enabledelayedexpansion

set ROLE=%~1
set TASK=%~2

if "%ROLE%"=="" (
    echo.
    echo   Minion Spawner
    echo   ==============
    echo.
    echo   Usage: spawn.bat ^<role^> ["task instructions"]
    echo.
    echo   Available roles:
    for %%f in ("%~dp0roles\*.md") do (
        echo     - %%~nf
    )
    echo.
    echo   Examples:
    echo     spawn architect
    echo     spawn builder "fix the template leakage bug in engine.py"
    echo     spawn explorer "brainstorm new seed topics for the curiosity engine"
    echo.
    exit /b 1
)

REM Check if role exists
if not exist "%~dp0roles\%ROLE%.md" (
    echo Error: Role "%ROLE%" not found.
    echo Available roles:
    for %%f in ("%~dp0roles\*.md") do echo   - %%~nf
    exit /b 1
)

REM Prepare workspace
echo Preparing workspace for %ROLE%...
if "%TASK%"=="" (
    python "%~dp0prepare.py" %ROLE%
) else (
    python "%~dp0prepare.py" %ROLE% --task "%TASK%"
)

if errorlevel 1 (
    echo Error preparing workspace.
    exit /b 1
)

REM Determine workspace name — check if personality exists
set WORKSPACE_NAME=%ROLE%
for %%f in ("%~dp0personalities\*-%ROLE%.md") do (
    set "PFILE=%%~nf"
    for /f "tokens=1 delims=-" %%a in ("!PFILE!") do (
        set WORKSPACE_NAME=%%a
    )
)

set WORKSPACE=%~dp0workspaces\%WORKSPACE_NAME%

REM Determine minion name for messaging
set MINION_NAME=%WORKSPACE_NAME%
for %%f in ("%~dp0personalities\*-%ROLE%.md") do (
    set "PFILE=%%~nf"
    for /f "tokens=1 delims=-" %%a in ("!PFILE!") do (
        set MINION_NAME=%%a
    )
)

REM Spawn in new Windows Terminal tab with MINION_NAME env var
echo Spawning %ROLE% as %MINION_NAME% in new terminal...
start wt -w 0 nt --title "Minion: %MINION_NAME% (%ROLE%)" cmd /k "set MINION_NAME=%MINION_NAME% && cd /d %WORKSPACE% && claude -n minion-%ROLE%"

echo.
echo Minion spawned! Check the new terminal tab.
echo Workspace: %WORKSPACE%
echo.
