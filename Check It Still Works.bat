@echo off
title Check the Cupboard App
cd /d "%~dp0"
echo Running every check. This takes about half a minute...
echo.
python tools\check_all.py
echo.
echo ---------------------------------------------
echo You want to see: 22 cabinets reproduce exactly
echo             and: 0 wrong
echo (the 22 needs the Wardrobes xlsx - laptops only)
echo ---------------------------------------------
echo.
pause
