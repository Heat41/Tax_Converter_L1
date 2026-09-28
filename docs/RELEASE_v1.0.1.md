# TAX_CONVERTER L-1 — Release v1.0.1

Status: **FINAL**

## Release gate

- Final UAT: PASS
- Packaging Readiness Bagian 1–3: PASS
- One-click Inno Setup build: PASS
- Installer build: PASS
- Install test: PASS
- Uninstall test: PASS

## Packaging

- PyInstaller: onedir
- Installer: Inno Setup 6
- Platform: Windows x64
- App version: 1.0.1
- Runtime database: `%LOCALAPPDATA%\TaxConverterL1\data\tax_converter.db`
- Coretax templates: 6 official L-1 templates bundled in application resources

## Final artifact

Expected installer:

```text
TaxConverterL1-Setup-v1.0.1-win64.exe
```

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\finalize_release.ps1
```

The command copies the already-tested installer into `release\v1.0.1`, generates SHA-256,
creates `release_manifest.json`, and writes release notes without rebuilding the application.
