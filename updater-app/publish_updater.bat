@echo off
setlocal
cd /d "%~dp0"

where dotnet >nul 2>nul
if errorlevel 1 (
  echo ERROR: .NET 8 SDK not found.
  pause
  exit /b 1
)

if exist "publish" rmdir /S /Q "publish"

dotnet publish "BigWalkHideSeek.Updater.csproj" ^
  -c Release ^
  -r win-x64 ^
  --self-contained true ^
  -p:PublishSingleFile=true ^
  -p:EnableCompressionInSingleFile=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true ^
  -p:DebugType=None ^
  -o "publish"

if errorlevel 1 (
  echo.
  echo BUILD FAILED.
  pause
  exit /b 1
)

echo.
echo Updater built:
echo   %~dp0publish\BigWalkHideSeek.Updater.exe
echo.
pause
