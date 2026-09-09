from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Agar script tetap bisa dijalankan langsung dengan:
# python scripts/export_legacy_pdf.py ...
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtGui import QGuiApplication

from config.database import init_database
from core.legacy_1770 import Legacy1770DocumentService
from core.legacy_pdf_exporter import Legacy1770PdfExporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export snapshot FINAL ke PDF Format Lama 1770 untuk uji visual Stage 8C."
    )
    parser.add_argument("--npwp", required=True, help="NPWP 15/16 digit")
    parser.add_argument("--tahun", required=True, type=int, help="Tahun Pajak")
    parser.add_argument("--output", required=True, help="Path PDF output")
    args = parser.parse_args()

    # QPdfWriter/QPainter membutuhkan QGuiApplication agar akses font database
    # aman saat script dijalankan sebagai CLI di luar aplikasi desktop utama.
    gui_app = QGuiApplication.instance()
    owns_gui_app = gui_app is None
    if gui_app is None:
        gui_app = QGuiApplication([sys.argv[0]])

    try:
        init_database()
        document = Legacy1770DocumentService().build_active_final(args.npwp, args.tahun)
        if not document.can_export_pdf:
            print("Export diblokir:")
            for issue in document.errors:
                print(f"- [{issue.code}] {issue.message}")
            return 2

        if document.warnings:
            print("Peringatan:")
            for issue in document.warnings:
                print(f"- [{issue.code}] {issue.message}")

        output = Legacy1770PdfExporter().export(document, Path(args.output))
        print(f"PDF berhasil dibuat: {output}")
        print(f"Revision FINAL: {document.revision}")
        print(f"Snapshot Hash: {document.snapshot_hash}")
        return 0
    finally:
        if owns_gui_app:
            gui_app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
