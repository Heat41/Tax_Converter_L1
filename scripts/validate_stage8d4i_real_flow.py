from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_mapping import ReverseCoretaxMappingService
from core.reverse_coretax_official_package import OfficialCoretaxPackageExporter
from core.reverse_coretax_official_package_validator import (
    OfficialCoretaxPackageValidator,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8D.4I - validasi end-to-end data nyata dari snapshot FINAL "
            "ke paket Coretax fleksibel."
        )
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--template-dir",
        required=True,
        help=(
            "Folder template Coretax asli. Hanya template untuk kategori "
            "yang benar-benar memiliki data yang wajib tersedia."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Folder hasil. Default: "
            "output/stage8d4i_<npwp>_<tahun>"
        ),
    )
    args = parser.parse_args()

    clean_npwp = "".join(
        ch for ch in str(args.npwp) if ch.isdigit()
    )
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT / "output" / f"stage8d4i_{clean_npwp}_{args.tahun}"
    )

    reverse_package = ReverseCoretaxMappingService().build_active_final(
        clean_npwp,
        args.tahun,
    )

    if not reverse_package.can_export:
        print("GAGAL - snapshot FINAL belum dapat direverse-export.")
        for issue in reverse_package.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    active_categories = [
        category
        for category, rows in reverse_package.rows_by_category.items()
        if rows
    ]

    print(f"NPWP             : {reverse_package.npwp}")
    print(f"Nama WP          : {reverse_package.nama_wp}")
    print(f"Tahun Pajak      : {reverse_package.tahun_pajak}")
    print(f"Revision FINAL   : {reverse_package.revision}")
    print(f"Total Harta      : {reverse_package.total_rows} baris")
    print(f"Kategori aktif   : {', '.join(active_categories)}")
    print("")

    export_result = OfficialCoretaxPackageExporter(
        args.template_dir
    ).export_package(
        reverse_package,
        output_dir,
    )

    for issue in export_result.issues:
        category = f" [{issue.category}]" if issue.category else ""
        print(
            f"[{issue.severity}] {issue.code}{category}: "
            f"{issue.message}"
        )

    if not export_result.ok:
        print("\nGAGAL - export paket Coretax tidak lengkap.")
        return 2

    validation = OfficialCoretaxPackageValidator().validate(
        output_dir
    )

    for issue in validation.issues:
        category = f" [{issue.category}]" if issue.category else ""
        print(
            f"[{issue.severity}] {issue.code}{category}: "
            f"{issue.message}"
        )

    if not validation.ok:
        print("\nGAGAL - paket hasil export tidak lolos validator.")
        return 2

    manifest = json.loads(
        (output_dir / "manifest.json").read_text(encoding="utf-8")
    )

    print("\nOK - Stage 8D.4I PASS")
    print(f"Output           : {output_dir}")
    print(
        f"Excel            : {manifest['excel']['file_count']} file"
    )
    print(
        f"XML              : {manifest['xml']['file_count']} file"
    )
    unsupported = manifest["xml"].get("unsupported_categories") or []
    if unsupported:
        print(
            "XML unsupported  : "
            + ", ".join(unsupported)
            + " (Excel tetap tersedia)"
        )
    else:
        print("XML unsupported  : -")

    print(
        "Prinsip          : hanya kategori/data yang tersedia "
        "yang diekspor; nilai yang tidak tersedia tidak dibuat-buat."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
