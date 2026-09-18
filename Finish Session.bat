@echo off
cd /d C:\Dev\CupboardApp
git add -A
set /p msg="What did you change? "
git commit -m "%msg%"
git push
echo.
echo Pushed. Safe to switch laptops.
pause