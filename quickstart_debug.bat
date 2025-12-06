@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Setup (Debug)

REM batファイルのあるディレクトリに移動
cd /d "%~dp0"

echo ============================================================
echo   JLTSQL Quickstart - Debug Mode
echo ============================================================
echo.

REM 環境変数 PYTHON が設定されていればそれを使用
if defined PYTHON (
    set PYTHON_EXE=%PYTHON%
    goto :run_python
)

REM py launcherからPythonのパスを取得
for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)"') do set PYTHON_EXE=%%i

if not defined PYTHON_EXE (
    echo ERROR: Python が見つかりません
    echo Python 3.10以上をインストールしてください
    pause
    exit /b 1
)

:run_python
echo Using: %PYTHON_EXE%
echo Arguments: %*
echo.
"%PYTHON_EXE%" scripts/quickstart.py %*

echo.
echo ============================================================
echo   終了コード: %errorlevel%
echo ============================================================
echo.
echo   エラーが発生した場合は上記のトレースバックを確認してください。
echo.
pause
