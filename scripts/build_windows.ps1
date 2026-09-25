$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==============================================="
Write-Host "BUILD TAX_CONVERTER L-1 - Stage 8E.2"
Write-Host "==============================================="

$python = Get-Command python -ErrorAction Stop

$template = Join-Path $root "resources\templates\1770\1770_master_bersih_6_halaman.pdf"
if (-not (Test-Path $template)) {
    throw "Template 1770 tidak ditemukan: $template"
}

$coretaxTemplateDir = Join-Path $root "resources\templates\coretax"
if (-not (Test-Path $coretaxTemplateDir)) {
    throw "Folder template Coretax tidak ditemukan: $coretaxTemplateDir"
}

$coretaxTemplates = Get-ChildItem $coretaxTemplateDir -Recurse -File -Filter *.xlsx
if ($coretaxTemplates.Count -lt 6) {
    throw "Template Coretax belum lengkap. Ditemukan $($coretaxTemplates.Count) file XLSX; minimal 6 file resmi wajib tersedia di: $coretaxTemplateDir"
}

$schemaFiles = @(
    "sql\schema_sqlite.sql",
    "sql\schema_pph_state.sql",
    "sql\schema_finalization.sql",
    "sql\schema_export_audit.sql"
)
foreach ($relative in $schemaFiles) {
    $path = Join-Path $root $relative
    if (-not (Test-Path $path)) {
        throw "Schema wajib tidak ditemukan: $path"
    }
}

try {
    python -c "import PyInstaller" | Out-Null
}
catch {
    throw "PyInstaller belum terpasang. Jalankan: python -m pip install pyinstaller"
}

Write-Host ""
Write-Host "[0/3] Membuat icon aplikasi..."
python .\scripts\generate_app_icon.py
if ($LASTEXITCODE -ne 0) {
    throw "Pembuatan icon aplikasi gagal dengan exit code $LASTEXITCODE"
}
$icon = Join-Path $root "resources\branding\tax_converter_l1.ico"
if (-not (Test-Path $icon)) {
    throw "Icon aplikasi tidak ditemukan setelah generator dijalankan: $icon"
}

Write-Host "[1/3] Membersihkan build lama..."
if (Test-Path (Join-Path $root "build")) {
    Remove-Item (Join-Path $root "build") -Recurse -Force
}
if (Test-Path (Join-Path $root "dist\TaxConverterL1")) {
    Remove-Item (Join-Path $root "dist\TaxConverterL1") -Recurse -Force
}

Write-Host "[2/3] Menjalankan PyInstaller..."
python -m PyInstaller --noconfirm --clean "TaxConverterL1.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller gagal dengan exit code $LASTEXITCODE"
}

$exe = Join-Path $root "dist\TaxConverterL1\TaxConverterL1.exe"
if (-not (Test-Path $exe)) {
    throw "Build selesai tetapi EXE tidak ditemukan: $exe"
}

Write-Host "[3/3] Verifikasi struktur build..."
$required = @(
    $exe,
    (Join-Path $root "dist\TaxConverterL1\_internal\sql\schema_sqlite.sql"),
    (Join-Path $root "dist\TaxConverterL1\_internal\resources\templates\1770\1770_master_bersih_6_halaman.pdf"),
    (Join-Path $root "dist\TaxConverterL1\_internal\resources\templates\coretax")
)
foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Artifact wajib tidak ditemukan pada build: $path"
    }
}

Write-Host ""
Write-Host "BUILD PASS"
Write-Host "EXE: $exe"
Write-Host "Database runtime akan dibuat di:"
Write-Host "  $env:LOCALAPPDATA\TaxConverterL1\data\tax_converter.db"
