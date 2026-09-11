from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.physical_reconciliation import PhysicalSourceExportReconciler


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8D.4K - bandingkan file Coretax sumber dengan hasil "
            "reverse-export fisik."
        )
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Folder file Coretax sumber WP yang berisi data.",
    )
    parser.add_argument(
        "--export-dir",
        required=True,
        help="Folder paket hasil reverse-export.",
    )
    args = parser.parse_args()

    result = PhysicalSourceExportReconciler().reconcile(
        args.source_dir,
        args.export_dir,
    )

    print("STAGE 8D.4K - PHYSICAL RECONCILIATION")
    print("=" * 88)

    for category, detail in result.categories.items():
        excel_status = (
            "PASS" if detail.excel_match is True
            else "FAIL" if detail.excel_match is False
            else "-"
        )
        xml_status = (
            "PASS" if detail.xml_match is True
            else "FAIL" if detail.xml_match is False
            else "-"
        )

        print(
            f"{category:10} | "
            f"Excel {detail.source_excel_rows}->{detail.exported_excel_rows} "
            f"{excel_status:4} | "
            f"XML {detail.source_xml_rows}->{detail.exported_xml_rows} "
            f"{xml_status:4}"
        )

    if result.issues:
        print("\nHASIL PEMERIKSAAN")
        print("-" * 88)
        for issue in result.issues:
            location = ""
            if issue.category:
                location += f" [{issue.category}]"
            if issue.row_number:
                location += f" baris {issue.row_number}"
            if issue.field_name:
                location += f" field {issue.field_name}"
            print(
                f"[{issue.severity}] {issue.code}{location}: "
                f"{issue.message}"
            )

    if result.ok:
        print(
            "\nOK - Stage 8D.4K PASS: isi sumber dan hasil export konsisten."
        )
        return 0

    print("\nGAGAL - ditemukan perbedaan source vs reverse-export.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
