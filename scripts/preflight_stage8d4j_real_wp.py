from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.real_wp_preflight import (
    RealWpPreflightService,
    list_final_snapshots,
)


def _print_final_list(db_path=None) -> int:
    rows = list_final_snapshots(db_path=db_path)

    if not rows:
        print("Belum ada snapshot FINAL pada database.")
        return 0

    print("SNAPSHOT FINAL TERSEDIA")
    print("=" * 88)
    for row in rows:
        print(
            f"NPWP: {row['npwp']} | "
            f"Nama: {row['nama_wp']} | "
            f"Tahun: {row['tahun_pajak']} | "
            f"Revision: {row['revision']} | "
            f"Final: {row['finalized_at']}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8D.4J - preflight/audit WP nyata sebelum export Coretax."
        )
    )
    parser.add_argument("npwp", nargs="?")
    parser.add_argument("tahun", nargs="?", type=int)
    parser.add_argument(
        "--template-dir",
        default=None,
        help=(
            "Folder template Coretax asli. Jika diberikan, preflight juga "
            "mengecek template yang dibutuhkan oleh kategori aktif."
        ),
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path database SQLite. Default memakai database aplikasi.",
    )
    parser.add_argument(
        "--list-final",
        action="store_true",
        help="Tampilkan semua snapshot FINAL yang tersedia.",
    )
    args = parser.parse_args()

    if args.list_final:
        return _print_final_list(args.db_path)

    if not args.npwp or not args.tahun:
        parser.error(
            "npwp dan tahun wajib diisi kecuali menggunakan --list-final"
        )

    result = RealWpPreflightService(
        db_path=args.db_path,
        template_dir=args.template_dir,
    ).inspect(
        args.npwp,
        args.tahun,
    )

    package = result.package

    print(f"NPWP           : {package.npwp or '-'}")
    print(f"Nama WP        : {package.nama_wp or '-'}")
    print(f"Tahun Pajak    : {package.tahun_pajak or '-'}")
    print(f"Revision FINAL : {package.revision or '-'}")
    print(f"Total Harta    : {package.total_rows}")
    print(
        "Kategori aktif : "
        + (", ".join(result.active_categories) or "-")
    )
    print("")

    for category in result.active_categories:
        count = result.category_counts.get(category, 0)
        schema_xml = "YA" if category in {
            "KAS", "INVESTASI", "BERGERAK", "HTB"
        } else "TIDAK"
        template = result.template_files.get(category)

        print(
            f"{category:10} : {count:>3} baris | "
            f"XML schema: {schema_xml} | "
            f"Template: {template.name if template else '-'}"
        )

    if result.missing_metadata:
        print("\nFIELD SUMBER YANG KOSONG")
        print("-" * 88)
        for category, rows in result.missing_metadata.items():
            for row_number, fields in rows.items():
                print(
                    f"{category} baris {row_number}: "
                    + ", ".join(fields)
                )

    if result.issues:
        print("\nHASIL PREFLIGHT")
        print("-" * 88)
        for issue in result.issues:
            location = ""
            if issue.category:
                location += f" [{issue.category}]"
            if issue.row_number:
                location += f" baris {issue.row_number}"
            print(
                f"[{issue.severity}] {issue.code}{location}: "
                f"{issue.message}"
            )

    if not result.ready:
        print("\nBELUM SIAP - selesaikan ERROR sebelum export.")
        return 2

    print(
        "\nSIAP - WP dapat diekspor secara fleksibel sesuai data yang tersedia."
    )
    if result.warnings:
        print(
            "WARNING hanya menunjukkan field sumber kosong; "
            "nilai tersebut tetap dibiarkan kosong dan tidak dibuat-buat."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
