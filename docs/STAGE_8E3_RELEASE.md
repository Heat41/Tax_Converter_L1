# Stage 8E.3 - Release Packaging

Tahap ini membentuk paket distribusi final Windows dari hasil PyInstaller Stage 8E.2.

## Prasyarat

- Full regression PASS.
- Final UAT Stage 8E.1 PASS.
- Smoke test packaged app Stage 8E.2 PASS.
- Build terbaru tersedia di `dist/TaxConverterL1`.

## Membuat release

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_release.ps1
```

Versi dibaca langsung dari `config/settings.py -> APP_VERSION`.

Untuk versi `1.0.0`, output:

```text
release/
  TaxConverterL1-v1.0.0-win64/
    TaxConverterL1.exe
    _internal/
    release_manifest.json

  TaxConverterL1-v1.0.0-win64.zip
  TaxConverterL1-v1.0.0-win64.sha256.txt
  TaxConverterL1-v1.0.0-win64.release_manifest.json
```

## Safety gate

Script otomatis menggagalkan packaging jika menemukan:

- `*.db`
- `*.sqlite`
- `*.sqlite3`
- file runtime `tax_converter.db`, WAL, atau SHM

Database produksi tetap berada di:

```text
%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db
```

dan tidak pernah ikut ZIP release.

## Verifikasi release

Cek checksum:

```powershell
Get-FileHash .\release\TaxConverterL1-v1.0.0-win64.zip -Algorithm SHA256
Get-Content .\release\TaxConverterL1-v1.0.0-win64.sha256.txt
```

Nilai SHA-256 harus sama.

Kemudian lakukan clean-extract test:

1. salin ZIP ke folder lain;
2. extract;
3. jalankan `TaxConverterL1.exe`;
4. cek Dashboard, Import, Worksheet, Finalisasi, Preview, dan Export;
5. tutup lalu buka ulang;
6. pastikan data tersimpan di LOCALAPPDATA.

Setelah clean-extract test PASS, commit release dapat diberi tag `v1.0.0`.
