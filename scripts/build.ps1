param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = (Get-Location).Path
if (-not [Environment]::Is64BitProcess) { throw 'Use x64 Python / PowerShell' }
$destination = Join-Path (Get-Location) 'dist/YuAudit-Windows-x64'
if (Test-Path -LiteralPath $destination) { throw 'Destination already exists. Move previous build before rebuilding.' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $Python scripts/create_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed' }
& $Python scripts/demo_formats.py
if ($LASTEXITCODE -ne 0) { throw 'Demo fixture generation failed' }
& $Python scripts/licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Dependency license collection failed' }
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name YuAudit --icon assets/icon.ico --add-data 'assets;assets' --add-data 'demo;demo' --add-data 'THIRD_PARTY_LICENSES;THIRD_PARTY_LICENSES' --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module tkinter launch.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$destination = Join-Path (Get-Location) 'dist/YuAudit-Windows-x64'
if (Test-Path -LiteralPath $destination) { throw 'Destination already exists. Move previous build before rebuilding.' }
Move-Item -LiteralPath 'dist/YuAudit' -Destination $destination
Copy-Item README.md,README.zh-CN.md,LICENSE,CHANGELOG.md,THIRD_PARTY_NOTICES.md -Destination $destination
Copy-Item -LiteralPath 'demo' -Destination $destination -Recurse
Copy-Item -LiteralPath 'THIRD_PARTY_LICENSES' -Destination $destination -Recurse
foreach ($lang in @('zh', 'en')) {
    $env:YUAUDIT_DATA_DIR = Join-Path (Get-Location) "build/smoke-profile-$lang"
    $proof = "build/smoke-exe-$lang"
    $process = Start-Process -FilePath (Join-Path $destination 'YuAudit.exe') -ArgumentList '--smoke-test', $proof, '--language', $lang -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(90000)) { $process.Kill(); throw 'EXE smoke timed out' }
    if ($process.ExitCode -ne 0) { throw "EXE smoke failed: $($process.ExitCode)" }
    if (-not (Test-Path "$proof/smoke-$lang.json")) { throw 'Missing smoke proof' }
}
Compress-Archive -Path $destination -DestinationPath 'dist/YuAudit-Windows-x64.zip' -Force
& $Python scripts/verify_package_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Packaged license validation failed' }
$extracted = Join-Path (Get-Location) ('build/中文 空格解压验证-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss'))
Expand-Archive -LiteralPath 'dist/YuAudit-Windows-x64.zip' -DestinationPath $extracted
$savedPath = $env:PATH
$savedPythonPath = $env:PYTHONPATH
$savedPythonHome = $env:PYTHONHOME
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = ''
    $env:PYTHONHOME = ''
    $env:YUAUDIT_DATA_DIR = Join-Path $extracted '本地 数据'
    $process = Start-Process -FilePath (Join-Path $extracted 'YuAudit-Windows-x64/YuAudit.exe') -WorkingDirectory $extracted -ArgumentList '--smoke-test', 'smoke-proof', '--language', 'en' -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(90000)) { $process.Kill(); throw 'Extracted EXE smoke timed out' }
    if ($process.ExitCode -ne 0) { throw "Extracted EXE smoke failed: $($process.ExitCode)" }
    if (-not (Test-Path (Join-Path $extracted 'smoke-proof/smoke-en.json'))) { throw 'Missing extracted smoke proof' }
} finally {
    $env:PATH = $savedPath
    $env:PYTHONPATH = $savedPythonPath
    $env:PYTHONHOME = $savedPythonHome
}
Copy-Item -LiteralPath (Join-Path $extracted 'smoke-proof') -Destination 'build/smoke-extracted-zip' -Recurse
Write-Output 'Built and smoke-tested dist/YuAudit-Windows-x64/YuAudit.exe'
