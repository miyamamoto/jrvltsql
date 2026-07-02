@echo off
REM JVLinkBridge ビルドスクリプト
REM 前提: .NET 8 SDK がインストール済み (winget install Microsoft.DotNet.SDK.8)
REM 出力: bin\x86\Release\net8.0-windows\JVLinkBridge.exe

echo Building JVLinkBridge (x86)...
dotnet build -c Release
if %errorlevel% neq 0 (
    echo Build failed!
    exit /b 1
)
echo.
echo Build successful!
echo Output: bin\x86\Release\net8.0-windows\JVLinkBridge.exe
