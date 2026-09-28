$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "================================================"
Write-Host "PACKAGING READINESS AUDIT - TAX CONVERTER L-1"
Write-Host "================================================"

$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Pass($message) {
    Write-Host "[PASS] $message"
}

function Fail($message) {
    Write-Host "[FAIL] $message"
    $failures.Add($message)
}

function Warn($message) {
    Write-Host "[WARN] $message"
    $warnings.Add($message)
}

Write-Host ""
Write-Host "[1/7] Entry point dan runtime Python"
if (Test-Path (Join-Path $root "ui\app.py")) {
    Pass "Entry point ui\app.py tersedia"
}
else {
    Fail "Entry point ui\app.py tidak ditemukan"
}

try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $pythonVersion) {
        throw "Perintah python --version gagal dengan exit code $LASTEXITCODE"
    }

    $pythonBitness = python -c "import sys; print(64 if sys.maxsize > 2**32 else 32)"
    if ($LASTEXITCODE -ne 0 -or -not $pythonBitness) {
        throw "Pemeriksaan bitness Python gagal dengan exit code $LASTEXITCODE"
    }

    $pythonArch = python -c "import platform; print(platform.machine())"
    if ($LASTEXITCODE -ne 0 -or -not $pythonArch) {
        throw "Pemeriksaan arsitektur Python gagal dengan exit code $LASTEXITCODE"
    }

    $versionText = ($pythonVersion -replace '^Python\s+', '').Trim()
    $bitnessText = $pythonBitness.Trim()
    $archText = $pythonArch.Trim()

    Write-Host "       Python : $versionText"
    Write-Host "       Bitness: $bitnessText-bit"
    Write-Host "       Arch   : $archText"

    if ($bitnessText -ne "64") {
        Fail "Packaging Windows harus memakai Python 64-bit"
    }
    else {
        Pass "Python runtime 64-bit"
    }
}
catch {
    Fail "Python runtime tidak dapat diperiksa: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[2/7] Dependency runtime/build"
$runtimeModules = @(
    @{ Module = "PySide6"; Label = "PySide6" },
    @{ Module = "pandas"; Label = "pandas" },
    @{ Module = "openpyxl"; Label = "openpyxl" },
    @{ Module = "pypdf"; Label = "pypdf" },
    @{ Module = "reportlab"; Label = "reportlab" }
)
foreach ($item in $runtimeModules) {
    $module = $item.Module
    $label = $item.Label
    try {
        $version = python -c "import importlib.metadata as m; print(m.version('$module'))"
        Pass "$label tersedia (v$($version.Trim()))"
    }
    catch {
        Fail "$label belum tersedia pada environment build"
    }
}

$buildModules = @(
    @{ Module = "PyInstaller"; Distribution = "pyinstaller"; Label = "PyInstaller" },
    @{ Module = "PIL"; Distribution = "Pillow"; Label = "Pillow" }
)
foreach ($item in $buildModules) {
    try {
        $version = python -c "import importlib.metadata as m; print(m.version('$($item.Distribution)'))"
        Pass "$($item.Label) tersedia (v$($version.Trim()))"
    }
    catch {
        Fail "$($item.Label) belum tersedia pada environment build"
    }
}

Write-Host ""
Write-Host "[3/7] Resource bundle"
$requiredFiles = @(
    "sql\schema_sqlite.sql",
    "sql\schema_pph_state.sql",
    "sql\schema_finalization.sql",
    "sql\schema_export_audit.sql",
    "resources\templates\1770\1770_master_bersih_6_halaman.pdf"
)
foreach ($relative in $requiredFiles) {
    $path = Join-Path $root $relative
    if (Test-Path $path) {
        Pass $relative
    }
    else {
        Fail "Resource wajib hilang: $relative"
    }
}

$coretaxDir = Join-Path $root "resources\templates\coretax"
if (-not (Test-Path $coretaxDir)) {
    Fail "Folder resources\templates\coretax tidak ditemukan"
}
else {
    $templates = @(Get-ChildItem $coretaxDir -File -Filter *.xlsx)
    if ($templates.Count -eq 6) {
        Pass "Template Coretax lengkap 6/6"
    }
    elseif ($templates.Count -lt 6) {
        Fail "Template Coretax hanya $($templates.Count)/6"
    }
    else {
        Warn "Ditemukan $($templates.Count) template Coretax; pastikan hanya versi resmi yang diperlukan"
    }
}

Write-Host ""
Write-Host "[4/7] Kontrak path aplikasi"
try {
    $pathInfo = python -c "from config.settings import BASE_DIR,RESOURCE_DIR,SQL_DIR,CORETAX_TEMPLATE_DIR,LEGACY_1770_TEMPLATE_DIR,SQLITE_DB_PATH,IS_FROZEN; print(BASE_DIR); print(RESOURCE_DIR); print(SQL_DIR); print(CORETAX_TEMPLATE_DIR); print(LEGACY_1770_TEMPLATE_DIR); print(SQLITE_DB_PATH); print(IS_FROZEN)"
    $lines = @($pathInfo)
    Write-Host "       BASE_DIR       : $($lines[0])"
    Write-Host "       RESOURCE_DIR   : $($lines[1])"
    Write-Host "       SQL_DIR        : $($lines[2])"
    Write-Host "       CORETAX        : $($lines[3])"
    Write-Host "       TEMPLATE 1770  : $($lines[4])"
    Write-Host "       DB development : $($lines[5])"
    Pass "Path resource dapat di-resolve dari config.settings"
}
catch {
    Fail "Path resource gagal di-resolve: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[5/7] Writable runtime data"
$localAppData = if ($env:LOCALAPPDATA) {
    $env:LOCALAPPDATA
}
else {
    Join-Path $HOME "AppData\Local"
}
$runtimeDir = Join-Path $localAppData "TaxConverterL1"
try {
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    $probe = Join-Path $runtimeDir ".packaging_write_probe"
    "ok" | Set-Content $probe -Encoding ASCII
    Remove-Item $probe -Force
    Pass "Runtime data writable: $runtimeDir"
}
catch {
    Fail "Runtime data tidak writable: $runtimeDir"
}

Write-Host ""
Write-Host "[6/7] Audit hard-coded path produksi"
$sourceRoots = @(
    (Join-Path $root "config"),
    (Join-Path $root "core"),
    (Join-Path $root "ui")
)
$hardcoded = @()
foreach ($sourceRoot in $sourceRoots) {
    if (-not (Test-Path $sourceRoot)) {
        continue
    }
    $hardcoded += Get-ChildItem $sourceRoot -Recurse -File -Filter *.py |
        Select-String -Pattern '(?i)([A-Z]:\\\\|[A-Z]:/|Users\\\\|Users/)' |
        Where-Object {
            $_.Line -notmatch 'LOCALAPPDATA' -and
            $_.Line -notmatch 'Program Files'
        }
}
if ($hardcoded.Count -eq 0) {
    Pass "Tidak ditemukan hard-coded absolute Windows path pada config/core/ui"
}
else {
    foreach ($match in $hardcoded) {
        Write-Host "       $($match.Path):$($match.LineNumber): $($match.Line.Trim())"
    }
    Fail "Hard-coded absolute path ditemukan pada source produksi"
}

Write-Host ""
Write-Host "[7/7] Database/resource leakage"
$forbidden = @()
$scanDirs = @(
    (Join-Path $root "resources"),
    (Join-Path $root "sql")
)
foreach ($dir in $scanDirs) {
    if (Test-Path $dir) {
        $forbidden += Get-ChildItem $dir -Recurse -File | Where-Object {
            $_.Extension -in @(".db", ".sqlite", ".sqlite3") -or
            $_.Name -match "^tax_converter\.db(?:-wal|-shm)?$"
        }
    }
}
if ($forbidden.Count -eq 0) {
    Pass "Tidak ada database user di resource bundle"
}
else {
    foreach ($file in $forbidden) {
        Write-Host "       $($file.FullName)"
    }
    Fail "Database user ditemukan di resource bundle"
}

Write-Host ""
Write-Host "================================================"
if ($failures.Count -eq 0) {
    Write-Host "PACKAGING READINESS BAGIAN 3 : PASS"
    if ($warnings.Count -gt 0) {
        Write-Host "Warning: $($warnings.Count)"
    }
    exit 0
}

Write-Host "PACKAGING READINESS BAGIAN 3 : FAIL"
Write-Host "Blocking issue: $($failures.Count)"
foreach ($item in $failures) {
    Write-Host " - $item"
}
exit 2
