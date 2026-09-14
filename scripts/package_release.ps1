$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==============================================="
Write-Host "RELEASE PACKAGING TAX_CONVERTER L-1 - Stage 8E.3"
Write-Host "==============================================="

$version = (python -c "from config.settings import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) {
    throw "APP_VERSION tidak dapat dibaca dari config/settings.py"
}

$distDir = Join-Path $root "dist\TaxConverterL1"
$exePath = Join-Path $distDir "TaxConverterL1.exe"
if (-not (Test-Path $exePath)) {
    throw "Build belum tersedia. Jalankan scripts\build_windows.ps1 terlebih dahulu."
}

$releaseRoot = Join-Path $root "release"
$releaseName = "TaxConverterL1-v$version-win64"
$releaseDir = Join-Path $releaseRoot $releaseName
$zipPath = Join-Path $releaseRoot "$releaseName.zip"
$checksumPath = Join-Path $releaseRoot "$releaseName.sha256.txt"
$externalManifestPath = Join-Path $releaseRoot "$releaseName.release_manifest.json"

Write-Host ""
Write-Host "[1/6] Menyiapkan folder release bersih..."
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
if (Test-Path $releaseDir) {
    Remove-Item $releaseDir -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
if (Test-Path $checksumPath) {
    Remove-Item $checksumPath -Force
}
if (Test-Path $externalManifestPath) {
    Remove-Item $externalManifestPath -Force
}
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Write-Host "[2/6] Menyalin build onedir..."
Copy-Item (Join-Path $distDir "*") $releaseDir -Recurse -Force

Write-Host "[3/6] Memeriksa artifact wajib dan data terlarang..."
$required = @(
    (Join-Path $releaseDir "TaxConverterL1.exe"),
    (Join-Path $releaseDir "_internal\sql\schema_sqlite.sql"),
    (Join-Path $releaseDir "_internal\sql\schema_pph_state.sql"),
    (Join-Path $releaseDir "_internal\sql\schema_finalization.sql"),
    (Join-Path $releaseDir "_internal\sql\schema_export_audit.sql"),
    (Join-Path $releaseDir "_internal\resources\templates\1770\1770_master_bersih_6_halaman.pdf")
)
foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Artifact wajib release tidak ditemukan: $path"
    }
}

$forbidden = Get-ChildItem $releaseDir -Recurse -File | Where-Object {
    $_.Extension -in @(".db", ".sqlite", ".sqlite3") -or
    $_.Name -match "^tax_converter\.db(?:-wal|-shm)?$"
}
if ($forbidden) {
    $names = ($forbidden | ForEach-Object FullName) -join [Environment]::NewLine
    throw "Release mengandung database user. Packaging dihentikan:$([Environment]::NewLine)$names"
}

$files = Get-ChildItem $releaseDir -Recurse -File
$totalBytes = ($files | Measure-Object Length -Sum).Sum
$fileCount = $files.Count
$exeHash = (Get-FileHash (Join-Path $releaseDir "TaxConverterL1.exe") -Algorithm SHA256).Hash.ToLowerInvariant()

$internalManifest = [ordered]@{
    product = "TAX_CONVERTER L-1"
    version = $version
    release_name = $releaseName
    platform = "windows-x64"
    packaging = "pyinstaller-onedir"
    file_count = $fileCount
    total_bytes = [int64]$totalBytes
    executable = "TaxConverterL1.exe"
    executable_sha256 = $exeHash
    database_runtime = "%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db"
    contains_user_database = $false
}
$internalManifest | ConvertTo-Json -Depth 5 | Set-Content (
    Join-Path $releaseDir "release_manifest.json"
) -Encoding UTF8

Write-Host "[4/6] Membuat ZIP release..."
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

if (-not (Test-Path $zipPath)) {
    throw "ZIP release gagal dibuat."
}

Write-Host "[5/6] Membuat checksum SHA-256..."
$zipHash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$zipHash  $releaseName.zip" | Set-Content $checksumPath -Encoding ASCII

$zipInfo = Get-Item $zipPath
$externalManifest = [ordered]@{
    product = "TAX_CONVERTER L-1"
    version = $version
    release_name = $releaseName
    platform = "windows-x64"
    packaging = "pyinstaller-onedir"
    zip_file = $zipInfo.Name
    zip_bytes = [int64]$zipInfo.Length
    zip_sha256 = $zipHash
    executable_sha256 = $exeHash
    source_dist = "dist/TaxConverterL1"
    database_runtime = "%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db"
    contains_user_database = $false
}
$externalManifest | ConvertTo-Json -Depth 5 | Set-Content $externalManifestPath -Encoding UTF8

Write-Host "[6/6] Verifikasi akhir release..."
$verifyHash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($verifyHash -ne $zipHash) {
    throw "Checksum ZIP berubah saat verifikasi."
}

Write-Host ""
Write-Host "RELEASE PACKAGE PASS"
Write-Host "Versi       : v$version"
Write-Host "Folder      : $releaseDir"
Write-Host "ZIP         : $zipPath"
Write-Host "Ukuran ZIP  : $([math]::Round($zipInfo.Length / 1MB, 2)) MB"
Write-Host "SHA-256     : $zipHash"
Write-Host "Checksum    : $checksumPath"
Write-Host "Manifest    : $externalManifestPath"
Write-Host ""
Write-Host "Database user TIDAK termasuk dalam paket release."
