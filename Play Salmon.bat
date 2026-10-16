@echo off
setlocal
title Tide and Tackle - Salmon Farmer
cd /d "%~dp0"
if errorlevel 1 goto setup_failed
set "PYGAME_HIDE_SUPPORT_PROMPT=1"

if exist ".venv\Scripts\python.exe" goto dependencies
echo Preparing the game for its first launch...
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv ".venv"
    goto environment_ready
)
where python >nul 2>&1
if errorlevel 1 goto python_missing
python -m venv ".venv"

:environment_ready
if not exist ".venv\Scripts\python.exe" goto setup_failed

:dependencies
".venv\Scripts\python.exe" -c "import pygame, av" >nul 2>&1
if not errorlevel 1 goto play
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 goto setup_failed
)
echo Installing the game's requirements. Internet is needed for this first setup.
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto setup_failed

:play
if /i "%~1"=="--check" (
    echo Ready to play Tide and Tackle.
    exit /b 0
)
echo Starting Tide and Tackle. You can leave this window behind the game.
".venv\Scripts\python.exe" "salmon_farm.py"
if errorlevel 1 goto game_failed
exit /b 0

:python_missing
echo Python is not installed or could not be found.
echo Install Python from https://www.python.org/downloads/windows/
echo Then double-click Play Salmon.bat again.
pause
exit /b 1

:setup_failed
echo.
echo The game could not finish setup. Check your internet connection and the error above.
echo Double-click Play Salmon.bat to try again.
pause
exit /b 1

:game_failed
echo.
echo The game stopped with an error. The details are shown above.
pause
exit /b 1
