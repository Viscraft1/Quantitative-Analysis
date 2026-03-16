@echo off
setlocal
title Quant Platform Stopper

cd /d "%~dp0"

set PID_FILE=.runtime\backend.pid

if not exist "%PID_FILE%" (
    echo [INFO] 未发现运行中的量化平台后台服务。
    pause
    exit /b 0
)

set /p APP_PID=<"%PID_FILE%"

if "%APP_PID%"=="" (
    echo [WARNING] PID 文件为空，已清理。
    del "%PID_FILE%" >nul 2>nul
    pause
    exit /b 0
)

taskkill /PID %APP_PID% /T /F >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] 无法结束 PID %APP_PID%，可能已经退出。
) else (
    echo [SUCCESS] 已关闭量化平台后台服务。
)

del "%PID_FILE%" >nul 2>nul
pause
