@echo off
rem Stops the Exam Digitizer web UI server.
setlocal
cd /d "%~dp0"
set "PORT=5000"
set "URL=http://127.0.0.1:%PORT%"

echo Stopping Exam Digitizer...

rem 1) Ask the server to shut itself down (same as the power button in the UI)
powershell -NoProfile -Command "try { Invoke-RestMethod -Method Post -Headers @{ 'X-Shutdown' = '1' } -TimeoutSec 3 '%URL%/api/shutdown' | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 echo The server did not answer; checking for a stuck process...

rem 2) If this app's Python server is still listening on the port, end it.
rem    Any other program using the port is left alone.
ping -n 3 127.0.0.1 >nul
powershell -NoProfile -Command "$ids = (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique; foreach ($i in $ids) { $p = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $i }; if ($p.CommandLine -like '*app*server.py*') { Stop-Process -Id $i -Force; Write-Host ('Force-stopped server process ' + $i) } elseif ($p) { Write-Host ('Port %PORT% is used by another program (' + $p.Name + '), not touching it.') } }"

echo Exam Digitizer is stopped.
ping -n 3 127.0.0.1 >nul
exit /b 0
