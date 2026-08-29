@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "PROFILE="
if exist "%~dp0thunderstore_profile_path.txt" set /p PROFILE=<"%~dp0thunderstore_profile_path.txt"
if not defined PROFILE (
  echo No Thunderstore profile configured. Run configure_profile.bat first.
  pause
  exit /b 1
)

set "COREURL=%~1"
if not defined COREURL set "COREURL=https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/BigWalkHideSeek.Core.dll"

where dotnet >nul 2>nul
if errorlevel 1 (
  echo ERROR: .NET SDK not found.
  pause
  exit /b 1
)

echo Building updateable Core...
dotnet build "core\BigWalkHideSeek.Core.csproj" -c Release -p:ProfilePath="%PROFILE%"
if errorlevel 1 (
  echo BUILD FAILED.
  pause
  exit /b 1
)

set "OUT=%~dp0publish"
if exist "%OUT%" rmdir /S /Q "%OUT%"
mkdir "%OUT%"
copy /Y "core\bin\Release\net6.0\BigWalkHideSeek.Core.dll" "%OUT%\BigWalkHideSeek.Core.dll" >nul

for /f "tokens=*" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%OUT%\BigWalkHideSeek.Core.dll').Hash.ToLower()"') do set "HASH=%%H"
for /f "tokens=*" %%V in ('powershell -NoProfile -Command "[System.Diagnostics.FileVersionInfo]::GetVersionInfo('%OUT%\BigWalkHideSeek.Core.dll').FileVersion"') do set "VERSION=%%V"

>"%OUT%\latest.json" echo {
>>"%OUT%\latest.json" echo   "version": "%VERSION%",
>>"%OUT%\latest.json" echo   "url": "%COREURL%",
>>"%OUT%\latest.json" echo   "sha256": "%HASH%"
>>"%OUT%\latest.json" echo }

echo.
echo Update package prepared:
echo   %OUT%\BigWalkHideSeek.Core.dll
echo   %OUT%\latest.json
echo.
echo Version: %VERSION%
echo SHA-256: %HASH%
echo.
echo Send the Core DLL to ChatGPT to publish it to the update feed.
echo.
pause
