@echo off
setlocal
title Quant Analysis Platform Launcher (Compatibility)

cd /d "%~dp0"

call "%~dp0launch.cmd"
exit /b %errorlevel%
