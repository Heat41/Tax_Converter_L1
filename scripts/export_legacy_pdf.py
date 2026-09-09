from __future__ import annotations

import argparse
from pathlib import Path

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


if __name__ == "__main__":
    raise SystemExit(main())
