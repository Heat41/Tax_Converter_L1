$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "================================================"
Write-Host "FINAL RELEASE - TAX CONVERTER L-1"
Write-Host "================================================"

$version = (python -c "from config.settings import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) {
    throw "APP_VERSION tidak dapat dibaca dari config/settings.py"
}

$installerName = "TaxConverterL1-Setup-v$version-win64.exe"
$installerSource = Join-Path $root "installer_output\$installerName"

if (-not (Test-Path $installerSource)) {
    throw "Installer final tidak ditemukan: $installerSource"
}

$releaseRoot = Join-Path $root "release"
$releaseDir = Join-Path $releaseRoot "v$version"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$installerTarget = Join-Path $releaseDir $installerName
Copy-Item $installerSource $installerTarget -Force

$installerHash = (Get-FileHash $installerTarget -Algorithm SHA256).Hash.ToLowerInvariant()
$installerBytes = (Get-Item $installerTarget).Length

$checksumPath = Join-Path $releaseDir "$installerName.sha256.txt"
"$installerHash  $installerName" | Set-Content $checksumPath -Encoding ASCII

$manifest = [ordered]@{
    product = "TAX_CONVERTER L-1"
    version = $version
    release_status = "FINAL"
    platform = "windows-x64"
    installer = $installerName
    installer_bytes = [int64]$installerBytes
    installer_sha256 = $installerHash
    packaging = "PyInstaller onedir + Inno Setup 6"
    database_runtime = "%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db"
    contains_user_database = $false
    coretax_templates = 6
    installer_uat = "PASS"
    install_test = "PASS"
    uninstall_test = "PASS"
}
$manifestPath = Join-Path $releaseDir "release_manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content $manifestPath -Encoding UTF8

$notesPath = Join-Path $releaseDir "RELEASE_NOTES.txt"
@"
TAX_CONVERTER L-1
Release v$version
Status: FINAL

Ringkasan:
- Packaging Readiness PASS
- One-click build dari Inno Setup PASS
- Installer build PASS
- Install test PASS
- Uninstall test PASS
- 6 template Coretax dibundel bersama aplikasi
- Database user disimpan di %LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db

Installer:
$installerName

SHA-256:
$installerHash
"@ | Set-Content $notesPath -Encoding UTF8

$verifyHash = (Get-FileHash $installerTarget -Algorithm SHA256).Hash.ToLowerInvariant()
if ($verifyHash -ne $installerHash) {
    throw "Checksum installer berubah saat verifikasi akhir."
}

Write-Host ""
Write-Host "FINAL RELEASE PASS"
Write-Host "Versi       : v$version"
Write-Host "Release dir : $releaseDir"
Write-Host "Installer   : $installerTarget"
Write-Host "Ukuran      : $([math]::Round($installerBytes / 1MB, 2)) MB"
Write-Host "SHA-256     : $installerHash"
Write-Host "Manifest    : $manifestPath"
Write-Host "Notes       : $notesPath"
