# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve()

datas = []

sql_dir = ROOT / "sql"
if sql_dir.is_dir():
    datas.append((str(sql_dir), "sql"))

resources_dir = ROOT / "resources"
if resources_dir.is_dir():
    datas.append((str(resources_dir), "resources"))

hiddenimports = [
    "PySide6.QtPdf",
]

a = Analysis(
    [str(ROOT / "ui" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Paket ML/data-science besar yang tersedia di environment development
        # tetapi tidak dipakai oleh Tax Converter. Tanpa exclude, hook PyInstaller
        # dapat menarik ratusan MB dependency opsional ke bundle.
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "sklearn",
        "scipy",
        "onnxruntime",
        "tensorflow",
        "pytest",
        "pyarrow",
        "faiss",
        "faiss_cpu",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TaxConverterL1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TaxConverterL1",
)
