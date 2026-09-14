param(
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "================================================"
Write-Host "BUILD INSTALLER TAX_CONVERTER L-1"
Write-Host "================================================"

$version = (python -c "from config.settings import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) {
    throw "APP_VERSION tidak dapat dibaca dari config/settings.py"
}

$versionParts = $version.Split(".")
if ($versionParts.Count -gt 4) {
    throw "APP_VERSION tidak valid untuk Windows version info: $version"
}
while ($versionParts.Count -lt 4) {
    $versionParts += "0"
}
$versionQuad = ($versionParts -join ".")

if (-not $SkipAppBuild) {
    Write-Host ""
    Write-Host "[1/5] Build aplikasi terbaru..."
    powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Build aplikasi gagal dengan exit code $LASTEXITCODE"
    }
}
else {
    Write-Host ""
    Write-Host "[1/5] Build aplikasi dilewati (-SkipAppBuild)."
}

$distDir = Join-Path $root "dist\TaxConverterL1"
$exe = Join-Path $distDir "TaxConverterL1.exe"
if (-not (Test-Path $exe)) {
    throw "Build aplikasi tidak ditemukan: $exe"
}

Write-Host "[2/5] Memastikan icon installer tersedia..."
python .\scripts\generate_app_icon.py
if ($LASTEXITCODE -ne 0) {
    throw "Pembuatan icon gagal dengan exit code $LASTEXITCODE"
}

$icon = Join-Path $root "resources\branding\tax_converter_l1.ico"
if (-not (Test-Path $icon)) {
    throw "Icon installer tidak ditemukan: $icon"
}

Write-Host "[3/5] Mencari Inno Setup Compiler..."
$candidates = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $iscc = $command.Source
    }
}

if (-not $iscc) {
    throw @"
Inno Setup 6 belum ditemukan.

Install Inno Setup 6 terlebih dahulu, lalu jalankan script ini lagi.
Website resmi: https://jrsoftware.org/isinfo.php
"@
}

Write-Host "Compiler: $iscc"

$installerOutput = Join-Path $root "installer_output"
if (Test-Path $installerOutput) {
    Remove-Item $installerOutput -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $installerOutput | Out-Null

Write-Host "[4/5] Compile installer v$version..."
$iss = Join-Path $root "installer\TaxConverterL1.iss"
& $iscc "/DMyAppVersion=$version" "/DMyAppVersionQuad=$versionQuad" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler gagal dengan exit code $LASTEXITCODE"
}

$setupExe = Join-Path $installerOutput "TaxConverterL1-Setup-v$version-win64.exe"
if (-not (Test-Path $setupExe)) {
    throw "Installer selesai dikompilasi tetapi file tidak ditemukan: $setupExe"
}

Write-Host "[5/5] Membuat checksum installer..."
$hash = (Get-FileHash $setupExe -Algorithm SHA256).Hash.ToLowerInvariant()
$checksum = Join-Path $installerOutput "TaxConverterL1-Setup-v$version-win64.sha256.txt"
"$hash  TaxConverterL1-Setup-v$version-win64.exe" | Set-Content $checksum -Encoding ASCII

$size = (Get-Item $setupExe).Length

Write-Host ""
Write-Host "INSTALLER BUILD PASS"
Write-Host "Versi       : v$version"
Write-Host "Installer   : $setupExe"
Write-Host "Ukuran      : $([math]::Round($size / 1MB, 2)) MB"
Write-Host "SHA-256     : $hash"
Write-Host "Checksum    : $checksum"
Write-Host ""
Write-Host "Default install:"
Write-Host "  C:\Program Files\TaxConverterL1"
Write-Host ""
Write-Host "Database user tetap di:"
Write-Host "  $env:LOCALAPPDATA\TaxConverterL1\data\tax_converter.db"
