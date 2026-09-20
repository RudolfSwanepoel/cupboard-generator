@echo off
title Check the Cupboard App
cd /d "%~dp0"
echo Checking the engine still produces the right numbers...
echo.
python tools\regen_check.py
echo.
python tools\check_examples.py
echo.
python tools\check_boards.py
echo.
python tools\check_edging.py
echo.
python tools\check_library.py
echo.
python tools\check_single_source.py
echo.
python tools\check_swap.py
echo.
echo ---------------------------------------------
echo You want to see: 22 cabinets reproduce exactly
echo             and: 0 wrong
echo ---------------------------------------------
echo.
pause
