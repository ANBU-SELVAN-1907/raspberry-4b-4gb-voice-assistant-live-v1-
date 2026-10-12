param([Parameter(Mandatory=$true)][string]$Port)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Port -notmatch '^COM[1-9][0-9]*$') { throw 'Enter a COM port such as COM5 from Device Manager.' }
$flasher = Join-Path $projectRoot 'runtime\flasher\esptool.exe'
$image = Join-Path $projectRoot 'esp32\build\jarvis_oled.ino.merged.bin'
$manifestPath = Join-Path $projectRoot 'esp32\build\firmware-manifest.json'
if (-not (Test-Path -LiteralPath $flasher) -or -not (Test-Path -LiteralPath $image) -or -not (Test-Path -LiteralPath $manifestPath)) {
    & "$PSScriptRoot\setup_esp32.ps1" -Port $Port
    exit $LASTEXITCODE
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.chip -ne 'esp32' -or $manifest.address -ne '0x0') { throw 'Firmware manifest does not target the classic ESP32.' }
if ((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLower() -ne $manifest.sha256) { throw 'Firmware checksum mismatch. Rebuild before flashing.' }
Write-Host "Flashing precompiled SSD1306 firmware to classic ESP32 on $Port. Close Jarvis and Serial Monitor first."
& $flasher --chip esp32 --port $Port --baud 460800 --before default_reset --after hard_reset write_flash 0x0 $image
if ($LASTEXITCODE -ne 0) { throw 'Upload failed. Check COM port, USB cable, and hold BOOT while connecting if required.' }
Write-Host 'Firmware uploaded. Run start.bat. No compiler or internet was used.'
