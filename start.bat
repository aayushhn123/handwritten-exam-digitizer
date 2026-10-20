@echo off
rem Starts the Exam Digitizer web UI and opens it in the default browser.
setlocal
cd /d "%~dp0"
title Exam Digitizer - starting
set "PORT=5000"
set "URL=http://127.0.0.1:%PORT%"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3 and try again.
    pause
    exit /b 1
)

call :is_up
if not errorlevel 1 (
    echo Exam Digitizer is already running. Opening %URL% ...
    start "" "%URL%"
    exit /b 0
)

echo Starting Exam Digitizer server...
rem The server runs in its own minimised window; closing that window or
rem running stop.bat (or the power button in the UI) stops it.
start "Exam Digitizer Server" /min python app\server.py

echo Waiting for the server to be ready...
for /l %%i in (1,1,60) do (
    call :is_up
    if not errorlevel 1 goto ready
    ping -n 2 127.0.0.1 >nul
)

echo.
echo The server did not start within 60 seconds.
echo Check the "Exam Digitizer Server" window for errors, e.g. a missing package:
echo     pip install -r requirements.txt
pause
exit /b 1

:ready
echo Server is ready. Opening %URL% ...
start "" "%URL%"
exit /b 0

:is_up
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%URL%/api/health' | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
exit /b %errorlevel%
