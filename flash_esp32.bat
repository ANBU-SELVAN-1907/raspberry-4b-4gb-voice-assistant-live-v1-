@echo off
setlocal
cd /d "%~dp0"
set /p "ESP_PORT=Enter the ESP32 COM port from Device Manager (example COM5): "
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\flash_prebuilt.ps1" -Port "%ESP_PORT%"
if errorlevel 1 echo ESP32 setup failed. Check the error above.
pause
