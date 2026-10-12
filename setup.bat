@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
  echo Setup failed. Fix the reported error and rerun setup.bat.
  pause
  exit /b 1
)
echo Setup complete. Double-click start.bat to use Jarvis.
pause
