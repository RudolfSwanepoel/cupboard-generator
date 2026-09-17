@echo off
title Cupboard App
cd /d "%~dp0"
echo Starting the Cupboard App...
echo.
python run_app.py
if errorlevel 1 (
  echo.
  echo ---------------------------------------------
  echo It did not start. The reason is above.
  echo Most likely Python is not installed yet.
  echo ---------------------------------------------
  echo.
  pause
)
