@echo off
title Make the Cupboard App desktop shortcut
cd /d "%~dp0"
rem Run once per laptop: pythonw's path is not the same on the two machines.
rem The shortcut uses the pythonw beside the python that "python" runs here,
rem so it is the same Python, with the same pywebview, as Start Cupboard App.bat.
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "PYW="
for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYW if exist "%%~dpPpythonw.exe" set "PYW=%%~dpPpythonw.exe"
if not defined PYW for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%P"
if not defined PYW (
  echo.
  echo ---------------------------------------------
  echo Could not find pythonw.exe. Is Python installed?
  echo ---------------------------------------------
  echo.
  pause
  exit /b 1
)
python -c "import webview" 2>nul
if errorlevel 1 echo Note: pywebview is not installed, so the app will open in the browser instead.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Cupboard App.lnk'; $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); $s.TargetPath = $env:PYW; $s.Arguments = '\"' + $env:REPO + '\run_app.py\"'; $s.WorkingDirectory = $env:REPO; $s.IconLocation = $env:REPO + '\app\cupboard.ico,0'; $s.Description = 'Cupboard App'; $s.WindowStyle = 1; $s.Save(); Write-Host ('Made ' + $lnk)"
if errorlevel 1 (
  echo.
  echo The shortcut was not made. The reason is above.
  echo.
  pause
  exit /b 1
)
echo.
echo   runs:     %PYW%
echo   start in: %REPO%
echo.
echo Double-click "Cupboard App" on the desktop to start it.
echo To pin it: right-click the shortcut, Show more options, Pin to taskbar.
echo.
pause
