param([switch]$SkipChecks)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:JARVIS_PROFILE = 'laptop'
$env:PYTHONUTF8 = '1'
$env:TEMP = Join-Path $projectRoot 'run\tmp'
$env:TMP = $env:TEMP
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    throw 'This bundle targets Windows 10/11 x64 Intel/AMD laptops.'
}
New-Item -ItemType Directory -Force runtime\python, runtime\downloads, run\tmp, vendor\windows, data\knowledge | Out-Null
function Get-Asset([string]$Url, [string]$Target, [string]$Sha256 = '') {
    if ((Test-Path -LiteralPath $Target) -and (-not $Sha256 -or (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLower() -eq $Sha256)) { return }
    $part = "$Target.part"
    for ($attempt=0; $attempt -lt 4; $attempt++) {
        try {
            Write-Host "Downloading $Url"
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $part
            if ($Sha256 -and (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLower() -ne $Sha256) { throw 'Download checksum mismatch' }
            Move-Item -LiteralPath $part -Destination $Target -Force
            return
        } catch { if ($attempt -eq 3) { throw }; Start-Sleep -Seconds (2 + $attempt) }
    }
}
function Invoke-Python([string[]]$PythonArgs) {
    & $script:pythonExe @PythonArgs
    if ($LASTEXITCODE -ne 0) { throw "Python step failed: $PythonArgs" }
}
$pythonZip = Join-Path $projectRoot 'runtime\downloads\python-3.13.16-embed-amd64.zip'
$pythonExe = Join-Path $projectRoot 'runtime\python\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Get-Asset 'https://www.python.org/ftp/python/3.13.16/python-3.13.16-embed-amd64.zip' $pythonZip
    Expand-Archive -LiteralPath $pythonZip -DestinationPath 'runtime\python' -Force
}
@('python313.zip', '.', 'Lib\site-packages', '..\..', 'import site') | Set-Content -LiteralPath 'runtime\python\python313._pth' -Encoding ASCII
if (-not (Test-Path -LiteralPath 'runtime\python\Lib\site-packages\pip')) {
    Get-Asset 'https://bootstrap.pypa.io/get-pip.py' 'runtime\downloads\get-pip.py'
    Invoke-Python @('runtime\downloads\get-pip.py', '--no-warn-script-location', '--disable-pip-version-check')
}
Invoke-Python @('-m','pip','install','--only-binary=:all:','--no-warn-script-location','--disable-pip-version-check','-r','requirements.txt')
if (-not (Test-Path -LiteralPath 'vendor\windows\llama-server.exe')) {
    $release = Invoke-RestMethod 'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest'
    $binaryRelease = $release
    $asset = $binaryRelease.assets | Where-Object { $_.name -match 'bin-win-cpu-x64\.zip$' } | Select-Object -First 1
    if (-not $asset) {
        $tagPath = Join-Path $projectRoot 'runtime\downloads\nightly-tag.txt'
        Get-Asset "https://github.com/ggml-org/llama.cpp/releases/download/$($release.tag_name)/nightly-tag.txt" $tagPath
        $tag = (Get-Content -Raw -LiteralPath $tagPath).Trim()
        if ($tag -notmatch '^b\d+$') { throw 'Unexpected upstream binary tag' }
        $binaryRelease = Invoke-RestMethod "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$tag"
        $asset = $binaryRelease.assets | Where-Object { $_.name -match 'bin-win-cpu-x64\.zip$' } | Select-Object -First 1
    }
    if (-not $asset) { throw 'Official Windows CPU llama.cpp asset not found' }
    $sha = if ($asset.digest) { $asset.digest -replace '^sha256:', '' } else { '' }
    Get-Asset $asset.browser_download_url 'runtime\downloads\llama-windows.zip' $sha
    Expand-Archive -LiteralPath 'runtime\downloads\llama-windows.zip' -DestinationPath 'vendor\windows' -Force
    if (-not (Test-Path -LiteralPath 'vendor\windows\llama-server.exe')) {
        $binary = Get-ChildItem 'vendor\windows' -Recurse -Filter 'llama-server.exe' | Select-Object -First 1
        if (-not $binary) { throw 'Archive did not contain llama-server.exe' }
        Copy-Item -Path (Join-Path $binary.Directory.FullName '*') -Destination 'vendor\windows' -Recurse -Force
    }
    @{ stable_release=$release.tag_name; binary_release=$binaryRelease.tag_name; sha256=$sha } | ConvertTo-Json | Set-Content 'runtime\llama-version.json' -Encoding UTF8
}
if (-not (Test-Path -LiteralPath 'config.laptop.json')) { Copy-Item 'config.laptop.example.json' 'config.laptop.json' }
if (-not (Test-Path -LiteralPath 'runtime\llama-version.json')) {
    $version = & 'vendor\windows\llama-server.exe' --version 2>&1 | Out-String
    @{ prepared_binary_version=$version.Trim(); source='official ggml-org Windows CPU release' } | ConvertTo-Json | Set-Content 'runtime\llama-version.json' -Encoding UTF8
}
Invoke-Python @('scripts\download_models.py')
if (-not (Test-Path -LiteralPath 'data\knowledge\assistant.md')) { Copy-Item 'knowledge_examples\assistant.md' 'data\knowledge\assistant.md' }
Invoke-Python @('scripts\index_knowledge.py')
if (-not $SkipChecks) {
    Invoke-Python @('-m','unittest','discover','-s','tests','-v')
    Invoke-Python @('scripts\doctor.py','--models','--verify-hashes')
    Invoke-Python @('scripts\model_smoke.py','--llama-binary','vendor/windows/llama-server.exe')
}
Invoke-Python @('scripts\record_runtime.py')
@{ python='3.13.16'; architecture='windows-x64'; completed_utc=[DateTime]::UtcNow.ToString('o') } | ConvertTo-Json | Set-Content 'runtime\setup-complete.json' -Encoding UTF8
Write-Host 'READY: start.bat runs offline. Transfer the complete folder with runtime/models/vendor included.'
