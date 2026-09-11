from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_official_package import OfficialCoretaxPackageExporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8D.4E/8D.4H - export paket Coretax sesuai kategori data: "
            "Excel + XML yang didukung + manifest."
        )
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--template-dir",
        required=True,
        help="Folder template Excel Coretax asli. Hanya template kategori berdata yang wajib tersedia.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Folder hasil. Default: output/coretax_official_<npwp>_<tahun>",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT / "output" / f"coretax_official_{clean_npwp}_{args.tahun}"
    )

    result = OfficialCoretaxPackageExporter(
        args.template_dir
    ).export_active_final(
        clean_npwp,
        args.tahun,
        output_dir,
    )

    for issue in result.issues:
        category = f" [{issue.category}]" if issue.category else ""
        print(
            f"[{issue.severity}] {issue.code}{category}: {issue.message}"
        )

    if not result.ok:
        print("\nGAGAL - paket resmi Coretax belum lengkap.")
        return 2

    print(f"\nOK - Paket resmi Coretax dibuat di: {result.output_dir}")
    print(f"Excel : {len(result.excel_result.files)} file")
    print(
        f"XML   : {len(result.xml_result.files)} file "
        f"(unsupported: {', '.join(result.xml_result.unsupported_categories)})"
    )
    print(f"Manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
