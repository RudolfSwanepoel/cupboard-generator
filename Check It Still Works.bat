@echo off
title Check the Cupboard App
cd /d "%~dp0"
echo Checking the engine still produces the right numbers...
echo.
python tools\regen_check.py
echo.
python tools\check_examples.py
echo.
echo ---------------------------------------------
echo You want to see: 22 cabinets reproduce exactly
echo             and: 0 wrong
echo ---------------------------------------------
echo.
pause
