$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist\TaxConverterL1"
$exe = Join-Path $dist "TaxConverterL1.exe"

Write-Host "==============================================="
Write-Host "SMOKE TEST BUILD - Stage 8E.2"
Write-Host "==============================================="

if (-not (Test-Path $exe)) {
    throw "EXE belum tersedia. Jalankan scripts\build_windows.ps1 terlebih dahulu."
}

$required = @(
    $exe,
    (Join-Path $dist "_internal\sql\schema_sqlite.sql"),
    (Join-Path $dist "_internal\sql\schema_pph_state.sql"),
    (Join-Path $dist "_internal\sql\schema_finalization.sql"),
    (Join-Path $dist "_internal\sql\schema_export_audit.sql"),
    (Join-Path $dist "_internal\resources\templates\1770\1770_master_bersih_6_halaman.pdf")
)

foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "FAIL - artifact wajib hilang: $path"
    }
}

Write-Host "[PASS] EXE tersedia"
Write-Host "[PASS] Semua schema SQLite tersedia"
Write-Host "[PASS] Template 1770 tersedia"
Write-Host ""
Write-Host "Jalankan EXE untuk smoke test UI:"
Write-Host "  $exe"
Write-Host ""
Write-Host "Setelah aplikasi terbuka, pastikan database muncul di:"
Write-Host "  $env:LOCALAPPDATA\TaxConverterL1\data\tax_converter.db"
