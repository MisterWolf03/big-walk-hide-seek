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

if not exist "%PROFILE%\BepInEx\core\BepInEx.Unity.IL2CPP.dll" (
  echo ERROR: BepInEx 6 IL2CPP was not found in this profile.
  pause
  exit /b 1
)

where dotnet >nul 2>nul
if errorlevel 1 (
  echo ERROR: The .NET SDK was not found.
  pause
  exit /b 1
)

echo Building Loader 0.1.1 only...
dotnet build "loader\BigWalkHideSeek.Loader.csproj" -c Release -p:ProfilePath="%PROFILE%"
if errorlevel 1 goto :buildfail

set "PLUGINDEST=%PROFILE%\BepInEx\plugins\BigWalkHideSeek"
if not exist "%PLUGINDEST%" mkdir "%PLUGINDEST%"

copy /Y "loader\bin\Release\net6.0\BigWalkHideSeek.Loader.dll" "%PLUGINDEST%\BigWalkHideSeek.Loader.dll" >nul
if errorlevel 1 goto :copyfail

echo.
echo SUCCESS.
echo Loader upgraded to 0.1.1.
echo Your installed Core and updater-config.json were NOT touched.
echo.
echo Launch Big Walk with Start modded normally.
echo The Loader should update Core 0.0.6 to 0.0.7 automatically.
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
echo ERROR: Loader build succeeded, but the DLL could not be copied.
echo Make sure Big Walk is fully closed and try again.
pause
exit /b 1
