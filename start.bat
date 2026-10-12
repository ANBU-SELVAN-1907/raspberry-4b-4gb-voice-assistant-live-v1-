@echo off
setlocal
cd /d "%~dp0"
set JARVIS_PROFILE=laptop
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
if not exist "runtime\python\python.exe" (
  echo First run: preparing the portable Windows environment...
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
  if errorlevel 1 goto failed
)
if not exist "runtime\setup-complete.json" (
  echo Setup is incomplete. Double-click setup.bat first.
  goto failed
)
"runtime\python\python.exe" scripts\launch_windows.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Jarvis could not start. Run diagnostics.bat and inspect the error above.
pause
exit /b 1
