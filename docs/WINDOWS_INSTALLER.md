# Windows Installer

Installer Windows dibuat dengan **Inno Setup 6** dari hasil build PyInstaller onedir.

## Prasyarat

1. Python environment project sudah siap.
2. Build aplikasi berhasil.
3. Inno Setup 6 terpasang.

Website resmi:

```text
https://jrsoftware.org/isinfo.php
```

## Build installer

Build aplikasi sekaligus installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

Jika `dist\TaxConverterL1` yang terbaru sudah tersedia dan tidak ingin menjalankan PyInstaller ulang:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 -SkipAppBuild
```

Output:

```text
installer_output/
  TaxConverterL1-Setup-v1.0.0-win64.exe
  TaxConverterL1-Setup-v1.0.0-win64.sha256.txt
```

## Perilaku installer

- Default lokasi instalasi: `C:\Program Files\TaxConverterL1`
- Shortcut Start Menu dibuat otomatis.
- Shortcut Desktop bersifat opsional pada wizard installer.
- Installer membutuhkan hak Administrator karena lokasi default berada di Program Files.
- Uninstaller dibuat otomatis oleh Inno Setup.
- Database user tidak disimpan di Program Files.

Database runtime tetap berada di:

```text
%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db
```

Karena itu update atau uninstall aplikasi tidak otomatis menghapus database user.

## Pengujian installer

Setelah build installer:

1. Jalankan `TaxConverterL1-Setup-v1.0.0-win64.exe`.
2. Selesaikan wizard instalasi.
3. Jalankan aplikasi dari Start Menu atau shortcut Desktop.
4. Verifikasi Dashboard, Import, Worksheet, Finalisasi, Preview, dan Export.
5. Tutup dan buka kembali aplikasi.
6. Verifikasi data runtime tetap berada di LOCALAPPDATA.
7. Uji uninstall dari Windows Apps/Installed apps.
