# Stage 8E.2 - Packaging & Deployment Desktop

Target awal release adalah Windows **PyInstaller onedir**.

## Alasan memilih onedir

- lebih stabil untuk PySide6/Qt;
- resource PDF 1770 dan schema SQL mudah diverifikasi;
- startup lebih cepat daripada onefile;
- update aplikasi tidak menyentuh database user.

## Lokasi data

Mode source/development:

```text
<repo>/data/tax_converter.db
```

Mode packaged:

```text
%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db
```

Database tidak dimasukkan ke bundle dan tidak disimpan di folder aplikasi.

## Resource yang wajib ikut build

- `sql/schema_sqlite.sql`
- `sql/schema_pph_state.sql`
- `sql/schema_finalization.sql`
- `sql/schema_export_audit.sql`
- `resources/templates/1770/1770_master_bersih_6_halaman.pdf`

## Build

Pasang PyInstaller bila belum ada:

```powershell
python -m pip install pyinstaller
```

Build:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Output:

```text
dist/
  TaxConverterL1/
    TaxConverterL1.exe
    _internal/
      sql/
      resources/
      ...
```

## Smoke test struktur

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test_build.ps1
```

Kemudian jalankan:

```powershell
.\dist\TaxConverterL1\TaxConverterL1.exe
```

Verifikasi manual:

1. aplikasi terbuka tanpa terminal Python;
2. Dashboard dan Worksheet dapat dibuka;
3. database dibuat/dibaca dari LOCALAPPDATA;
4. import workbook/Coretax dapat dilakukan;
5. preview Format Lama dapat membuka PDF;
6. preview Paket Coretax dapat dibuka;
7. export Format Lama berhasil;
8. export Paket Coretax berhasil;
9. tutup aplikasi, buka ulang, dan pastikan data tetap tersedia.

## Sebelum distribusi

Jalankan:

```powershell
python -m pytest -q
```

dan Final UAT Stage 8E.1 untuk WP uji nyata.

Folder `build/` dan `dist/` bersifat lokal dan di-ignore Git.
