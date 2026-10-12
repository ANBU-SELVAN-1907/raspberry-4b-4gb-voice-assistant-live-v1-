param([string]$Port = '', [switch]$CompileOnly)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $CompileOnly -and $Port -notmatch '^COM[1-9][0-9]*$') { throw 'Use a COM port such as COM5 from Device Manager.' }
New-Item -ItemType Directory -Force runtime\arduino, runtime\arduino-data, runtime\arduino-user, runtime\arduino-downloads, esp32\build | Out-Null
$cliExe = Join-Path $projectRoot 'runtime\arduino\arduino-cli.exe'
if (-not (Test-Path -LiteralPath $cliExe)) {
    $zip = Join-Path $projectRoot 'runtime\arduino-cli.zip'
    Invoke-WebRequest -UseBasicParsing 'https://github.com/arduino/arduino-cli/releases/download/v1.5.1/arduino-cli_1.5.1_Windows_64bit.zip' -OutFile $zip
    if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower() -ne 'fabe42e0eb04d00e776a66178299ff95a46c623dbc260f997e58fd514853dd40') { throw 'Arduino CLI checksum mismatch' }
    Expand-Archive -LiteralPath $zip -DestinationPath 'runtime\arduino' -Force
}
$configFile = Join-Path $projectRoot 'runtime\arduino-cli.yaml'
$config = @"
board_manager:
  additional_urls:
    - https://espressif.github.io/arduino-esp32/package_esp32_index.json
directories:
  data: '$($projectRoot.Replace('\','/'))/runtime/arduino-data'
  downloads: '$($projectRoot.Replace('\','/'))/runtime/arduino-downloads'
  user: '$($projectRoot.Replace('\','/'))/runtime/arduino-user'
"@
[IO.File]::WriteAllText($configFile, $config)
function Invoke-Arduino([string[]]$CliArgs) {
    & $script:cliExe --config-file $script:configFile @CliArgs
    if ($LASTEXITCODE -ne 0) { throw "Arduino step failed: $CliArgs" }
}
if (-not (Test-Path 'runtime\esp32-toolchain-ready.txt')) {
    Invoke-Arduino @('core','update-index')
    # Scope this local package index to classic ESP32 tooling. Other chip-family
    # compilers/debuggers consume several GB and are not used by this sketch.
    # Package URLs and official SHA256 checksums remain unchanged.
    $indexPath = Join-Path $projectRoot 'runtime\arduino-data\package_esp32_index.json'
    $index = Get-Content -Raw -LiteralPath $indexPath | ConvertFrom-Json
    $package = $index.packages | Where-Object name -eq 'esp32'
    $platform = $package.platforms | Where-Object version -eq '2.0.17'
    if (-not $platform) { throw 'Pinned classic ESP32 platform missing from official index' }
    $platform.toolsDependencies = @($platform.toolsDependencies | Where-Object { $_.name -in @('xtensa-esp32-elf-gcc','esptool_py','mkspiffs','mklittlefs') })
    [IO.File]::WriteAllText($indexPath, ($index | ConvertTo-Json -Depth 100), (New-Object Text.UTF8Encoding($false)))
    # Install only the classic compiler; source archive extraction excludes
    # other chip-family SDKs while retaining official package checksums.
    if (-not (Test-Path 'runtime\python\python.exe')) { throw 'Run setup.bat before building firmware.' }
    & 'runtime\python\python.exe' 'scripts\extract_classic_esp32.py'
    if ($LASTEXITCODE -ne 0) { throw 'Classic ESP32 SDK extraction failed' }
    Invoke-Arduino @('lib','install','Adafruit SSD1306','Adafruit GFX Library','ArduinoJson')
    'ready' | Set-Content 'runtime\esp32-toolchain-ready.txt'
}
# Short SDK paths avoid GCC's Windows command-line length limit with this
# project's space-containing directory and the large ESP-IDF include list.
if (-not ('JarvisShortPaths' -as [type])) { Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class JarvisShortPaths {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
  public static extern uint GetShortPathName(string path, StringBuilder result, uint length);
}
'@
}
$shortBuffer = New-Object Text.StringBuilder 32768
$shortLength = [JarvisShortPaths]::GetShortPathName($projectRoot, $shortBuffer, 32768)
$compileRoot = if ($shortLength -gt 0) { $shortBuffer.ToString().Replace('\','/') } else { $projectRoot.Replace('\','/') }
Invoke-Arduino @('compile','--fqbn','esp32:esp32:esp32','--build-path',"$compileRoot/runtime/esp32-compile",
    '--build-property',"compiler.sdk.path=$compileRoot/runtime/arduino-data/packages/esp32/hardware/esp32/2.0.17/tools/sdk/esp32",
    '--build-property',"compiler.path=$compileRoot/runtime/arduino-data/packages/esp32/tools/xtensa-esp32-elf-gcc/esp-2021r2-patch5-8.4.0/bin/",
    '--output-dir','esp32/build','esp32/jarvis_oled')
$esptool = Get-ChildItem 'runtime\arduino-data\packages\esp32\tools\esptool_py' -Recurse -Filter 'esptool.exe' | Select-Object -First 1
if (-not $esptool) { throw 'ESP32 build succeeded but the native flasher was not found' }
New-Item -ItemType Directory -Force 'runtime\flasher' | Out-Null
Copy-Item -Path (Join-Path $esptool.Directory.FullName '*') -Destination 'runtime\flasher' -Recurse -Force
$merged = 'esp32\build\jarvis_oled.ino.merged.bin'
if (-not (Test-Path -LiteralPath $merged)) {
    & 'runtime\flasher\esptool.exe' --chip esp32 merge_bin -o $merged --flash_mode keep --flash_freq keep --flash_size keep `
        0x1000 'esp32\build\jarvis_oled.ino.bootloader.bin' 0x8000 'esp32\build\jarvis_oled.ino.partitions.bin' `
        0xe000 'runtime\arduino-data\packages\esp32\hardware\esp32\2.0.17\tools\partitions\boot_app0.bin' `
        0x10000 'esp32\build\jarvis_oled.ino.bin'
    if ($LASTEXITCODE -ne 0) { throw 'Merging ESP32 firmware failed' }
}
@{ chip='esp32'; address='0x0'; fqbn='esp32:esp32:esp32'; sha256=(Get-FileHash -LiteralPath $merged -Algorithm SHA256).Hash.ToLower() } | ConvertTo-Json | Set-Content 'esp32\build\firmware-manifest.json' -Encoding UTF8
if (-not $CompileOnly) {
    Invoke-Arduino @('upload','--fqbn','esp32:esp32:esp32','--port',$Port,'--input-dir','esp32/build','esp32/jarvis_oled')
    Write-Host 'Uploaded. Close Serial Monitor, connect the OLED, and run start.bat.'
} else { Write-Host 'Firmware compiled successfully. Flash with flash_esp32.bat when your ESP32 is connected.' }
