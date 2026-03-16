@echo off
setlocal
title Quant Analysis Platform Launcher

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found.
    echo Please install Python 3.10+ and enable "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo ========================================================
echo        Quant Analysis Platform - One Click Launch
echo ========================================================
echo.
echo Checking environment and starting the app window...
echo.

python bootstrap.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Launch failed. Please review the logs above and try again.
    echo.
    pause
    exit /b %errorlevel%
)

exit /b 0
