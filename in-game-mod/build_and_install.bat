@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PROFILE="

if not "%~1"=="" set "PROFILE=%~1"

if not defined PROFILE (
  if exist "%~dp0thunderstore_profile_path.txt" (
    set /p PROFILE=<"%~dp0thunderstore_profile_path.txt"
  )
)

if not defined PROFILE (
  echo No Thunderstore profile has been configured yet.
  echo Opening the profile picker...
  call "%~dp0configure_profile.bat"
  if exist "%~dp0thunderstore_profile_path.txt" (
    set /p PROFILE=<"%~dp0thunderstore_profile_path.txt"
  )
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

for %%F in (UnityEngine.CoreModule.dll UnityEngine.IMGUIModule.dll UnityEngine.InputLegacyModule.dll) do (
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

echo Building Big Walk Hide + Seek prototype...
dotnet build BigWalkHideSeek.csproj -c Release -p:ProfilePath="%PROFILE%"
if errorlevel 1 (
  echo.
  echo BUILD FAILED.
  pause
  exit /b 1
)

set "DEST=%PROFILE%\BepInEx\plugins\BigWalkHideSeek"
if not exist "%DEST%" mkdir "%DEST%"

copy /Y "bin\Release\net6.0\BigWalkHideSeek.dll" "%DEST%\BigWalkHideSeek.dll" >nul
if errorlevel 1 (
  echo.
  echo ERROR: Build succeeded, but the DLL could not be copied.
  echo Destination:
  echo   %DEST%
  pause
  exit /b 1
)

echo.
echo SUCCESS.
echo Installed prototype to:
echo   %DEST%\BigWalkHideSeek.dll
echo.
echo Launch Big Walk with Start modded using THIS profile.
echo Then press F7 in-game.
echo.
pause
