@echo off
title Build the Cupboard App demo
cd /d "%~dp0"
rem One click: compiles the app with Nuitka, zips it into demo\ with READ ME FIRST.txt.
rem The demo stops working 60 days from today. To extend it, just build again.
rem   Build Demo.bat --test-expired   a throwaway copy that expired yesterday (a test)
echo Building the Cupboard App demo. The first build takes 10-20 minutes.
echo.
python tools\build_demo.py %*
if errorlevel 1 (
  echo.
  echo ---------------------------------------------
  echo The demo was NOT built, or is not safe to send. The reason is above.
  echo ---------------------------------------------
)
echo.
pause
