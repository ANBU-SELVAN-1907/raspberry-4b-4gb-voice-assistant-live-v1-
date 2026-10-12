@echo off
setlocal
cd /d "%~dp0"
set JARVIS_PROFILE=laptop
set PYTHONUTF8=1
if not exist "runtime\python\python.exe" (echo Run setup.bat first.& pause& exit /b 1)
"runtime\python\python.exe" scripts\test_oled.py
pause
