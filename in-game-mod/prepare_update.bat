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
if not defined COREURL set "COREURL=https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/BigWalkHideSeek.Core.gz.b64"

set "LOADER_VERSION=0.1.1.0"
set "LOADER_URL=https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/BigWalkHideSeek.Loader.gz.b64"
set "LOADER_SHA256=b4825436c31bad136e4dbd7c96bb4539bfaa72829350b30a266355c881e8f96e"

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

powershell -NoProfile -Command "$src=[IO.File]::ReadAllBytes('%OUT%\BigWalkHideSeek.Core.dll'); $ms=New-Object IO.MemoryStream; $gz=New-Object IO.Compression.GZipStream($ms,[IO.Compression.CompressionMode]::Compress,$true); $gz.Write($src,0,$src.Length); $gz.Dispose(); [IO.File]::WriteAllText('%OUT%\BigWalkHideSeek.Core.gz.b64',[Convert]::ToBase64String($ms.ToArray())); $ms.Dispose()"
if errorlevel 1 (
  echo ERROR: Could not create gzip/base64 update payload.
  pause
  exit /b 1
)

>"%OUT%\latest.json" echo {
>>"%OUT%\latest.json" echo   "version": "%VERSION%",
>>"%OUT%\latest.json" echo   "url": "%COREURL%",
>>"%OUT%\latest.json" echo   "sha256": "%HASH%",
>>"%OUT%\latest.json" echo   "encoding": "gzip-base64"
>>"%OUT%\latest.json" echo }

>"%OUT%\updater.json" echo {
>>"%OUT%\updater.json" echo   "schemaVersion": 1,
>>"%OUT%\updater.json" echo   "loader": {
>>"%OUT%\updater.json" echo     "version": "%LOADER_VERSION%",
>>"%OUT%\updater.json" echo     "url": "%LOADER_URL%",
>>"%OUT%\updater.json" echo     "sha256": "%LOADER_SHA256%",
>>"%OUT%\updater.json" echo     "encoding": "gzip-base64"
>>"%OUT%\updater.json" echo   },
>>"%OUT%\updater.json" echo   "core": {
>>"%OUT%\updater.json" echo     "version": "%VERSION%",
>>"%OUT%\updater.json" echo     "url": "%COREURL%",
>>"%OUT%\updater.json" echo     "sha256": "%HASH%",
>>"%OUT%\updater.json" echo     "encoding": "gzip-base64"
>>"%OUT%\updater.json" echo   },
>>"%OUT%\updater.json" echo   "releaseNotes": "Core %VERSION% update."
>>"%OUT%\updater.json" echo }

echo.
echo Update package prepared:
echo   %OUT%\BigWalkHideSeek.Core.dll
echo   %OUT%\BigWalkHideSeek.Core.gz.b64
echo   %OUT%\latest.json
echo   %OUT%\updater.json
echo.
echo Version: %VERSION%
echo SHA-256: %HASH%
echo.
echo To publish, upload these THREE files to feed/9f6d2a on branch bw-hs-feed-7c41e9:
echo   BigWalkHideSeek.Core.gz.b64
echo   latest.json
echo   updater.json
echo.
pause
