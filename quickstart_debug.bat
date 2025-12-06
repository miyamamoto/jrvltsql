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

REM Python 32bit版の実行パスを取得（py launcherを経由せず直接実行 - 高速化のため）
REM 環境変数 PYTHON32 が設定されていればそれを使用
if defined PYTHON32 (
    set PYTHON_EXE=%PYTHON32%
    goto :run_python
)

REM py launcherからPython 32bitのパスを取得
for /f "delims=" %%i in ('py -3-32 -c "import sys; print(sys.executable)"') do set PYTHON_EXE=%%i

if not defined PYTHON_EXE (
    echo ERROR: Python 32bit が見つかりません
    echo py -3-32 を実行できることを確認してください
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
