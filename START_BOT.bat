@echo off
cd /d "%~dp0"
title AnonXpress — Starting...

echo.
echo  =============================================
echo   AnonXpress — Starting tracking system...
echo  =============================================
echo.

:: Launch server.py in its own window (website tracking API)
start "AnonXpress Tracking Server" cmd /k "title AnonXpress Tracking Server && python server.py"

:: Small delay so server is ready before bot starts
timeout /t 2 /nobreak >nul

:: Launch bot.py in its own window (Telegram bot)
start "AnonXpress Telegram Bot" cmd /k "title AnonXpress Telegram Bot && python bot.py"

echo  Both services launched in separate windows.
echo.
echo  - Tracking Server : localhost:8080
echo  - Telegram Bot    : running
echo.
echo  Keep both windows open while operating.
echo  Close this window when done.
echo.
pause
