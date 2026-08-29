@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PROFILE="
if not "%~1"=="" set "PROFILE=%~1"

if not defined PROFILE (
  if exist "%~dp0thunderstore_profile_path.txt" set /p PROFILE=<"%~dp0thunderstore_profile_path.txt"
)

if not defined PROFILE (
  echo No Thunderstore profile has been configured yet.
  echo Opening the profile picker...
  call "%~dp0configure_profile.bat"
  if exist "%~dp0thunderstore_profile_path.txt" set /p PROFILE=<"%~dp0thunderstore_profile_path.txt"
)

if not defined PROFILE (
  echo.
  echo ERROR: No Thunderstore profile was selected.
  pause
  exit /b 1
)

echo.
echo Using Thunderstore profile:
echo   %PROFILE%
echo.

if not exist "%PROFILE%\BepInEx\core\BepInEx.Unity.IL2CPP.dll" (
  echo ERROR: BepInEx 6 IL2CPP was not found in this profile.
  pause
  exit /b 1
)

for %%F in (Assembly-CSharp.dll UnityEngine.CoreModule.dll UnityEngine.IMGUIModule.dll UnityEngine.InputLegacyModule.dll UnityEngine.TextRenderingModule.dll UnityEngine.ImageConversionModule.dll UnityEngine.PhysicsModule.dll) do (
  if not exist "%PROFILE%\BepInEx\interop\%%F" (
    echo ERROR: Required BepInEx interop file is missing:
    echo   %PROFILE%\BepInEx\interop\%%F
    echo.
    echo Launch Big Walk modded once through this profile, close it, then try again.
    pause
    exit /b 1
  )
)

where dotnet >nul 2>nul
if errorlevel 1 (
  echo ERROR: The .NET SDK was not found.
  echo Install the .NET 6 SDK, then try again.
  pause
  exit /b 1
)

echo Building permanent Loader...
dotnet build "loader\BigWalkHideSeek.Loader.csproj" -c Release -p:ProfilePath="%PROFILE%"
if errorlevel 1 goto :buildfail

echo.
echo Building updateable Core...
dotnet build "core\BigWalkHideSeek.Core.csproj" -c Release -p:ProfilePath="%PROFILE%"
if errorlevel 1 goto :buildfail

set "PLUGINDEST=%PROFILE%\BepInEx\plugins\BigWalkHideSeek"
set "RUNTIMEDEST=%PROFILE%\BepInEx\BigWalkHideSeek"
if not exist "%PLUGINDEST%" mkdir "%PLUGINDEST%"
if not exist "%RUNTIMEDEST%" mkdir "%RUNTIMEDEST%"

rem Remove the old all-in-one prototype so BepInEx cannot load both versions.
if exist "%PLUGINDEST%\BigWalkHideSeek.dll" del /Q "%PLUGINDEST%\BigWalkHideSeek.dll"

copy /Y "loader\bin\Release\net6.0\BigWalkHideSeek.Loader.dll" "%PLUGINDEST%\BigWalkHideSeek.Loader.dll" >nul
if errorlevel 1 goto :copyfail

copy /Y "core\bin\Release\net6.0\BigWalkHideSeek.Core.dll" "%RUNTIMEDEST%\BigWalkHideSeek.Core.dll" >nul
if errorlevel 1 goto :copyfail

if not exist "%RUNTIMEDEST%\updater-config.json" (
  >"%RUNTIMEDEST%\updater-config.json" echo {
  >>"%RUNTIMEDEST%\updater-config.json" echo   "enabled": true,
  >>"%RUNTIMEDEST%\updater-config.json" echo   "manifestUrl": "https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/latest.json",
  >>"%RUNTIMEDEST%\updater-config.json" echo   "bearerToken": "",
  >>"%RUNTIMEDEST%\updater-config.json" echo   "timeoutSeconds": 4
  >>"%RUNTIMEDEST%\updater-config.json" echo }
)

echo.
echo SUCCESS.
echo.
echo Permanent Loader:
echo   %PLUGINDEST%\BigWalkHideSeek.Loader.dll
echo.
echo Updateable Core:
echo   %RUNTIMEDEST%\BigWalkHideSeek.Core.dll
echo.
echo Automatic Core updates are enabled for this installation.
echo.
echo Launch Big Walk with Start modded and press F7.
echo.
pause
exit /b 0

:buildfail
echo.
echo BUILD FAILED.
pause
exit /b 1

:copyfail
echo.
echo ERROR: Build succeeded, but one of the DLLs could not be installed.
pause
exit /b 1
