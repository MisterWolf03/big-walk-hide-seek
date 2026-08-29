@echo off
setlocal
cd /d "%~dp0"

echo.
echo Big Walk Hide + Seek - Thunderstore profile setup
echo --------------------------------------------------
echo.
echo A folder picker will open.
echo In Thunderstore, use Settings ^> Browse profile folder,
echo then select that same PROFILE folder here.
echo.
pause

for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pick_thunderstore_profile.ps1"`) do set "PROFILE=%%P"

if not defined PROFILE (
  echo.
  echo No valid profile was selected.
  pause
  exit /b 1
)

> "%~dp0thunderstore_profile_path.txt" echo %PROFILE%

echo.
echo Saved Thunderstore profile:
echo   %PROFILE%
echo.
echo You can rerun this file any time to change profiles.
pause
