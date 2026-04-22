@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Daily Sync

cd /d "%~dp0"

if exist "%~dp0venv32\Scripts\python.exe" (
    set "PYTHON=%~dp0venv32\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo ============================================================
echo   JLTSQL Daily Sync
echo ============================================================
echo Using Python: %PYTHON%
echo.

"%PYTHON%" scripts\daily_update.py %*
exit /b %errorlevel%
