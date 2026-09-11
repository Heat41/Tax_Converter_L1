from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_excel import ReverseCoretaxExcelExporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 8D.2 - ekspor 6 file Excel L-1 dari snapshot FINAL."
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Folder hasil. Default: output/coretax_<npwp>_<tahun>",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT / "output" / f"coretax_{clean_npwp}_{args.tahun}"
    )

    result = ReverseCoretaxExcelExporter().export_active_final(
        clean_npwp,
        args.tahun,
        output_dir,
    )

    if not result.ok:
        print("GAGAL - 8D.2 belum dapat menghasilkan 6 file Excel.")
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    print(f"OK - 6 file Excel reverse Coretax dibuat di: {result.output_dir}")
    for category, path in result.files.items():
        print(
            f"{category:10} : {result.row_counts.get(category, 0):>3} baris -> "
            f"{path.name}"
        )

    for issue in result.issues:
        print(f"[{issue.severity}] {issue.code}: {issue.message}")

    print(
        "\nCATATAN: 8D.2 saat ini memakai schema yang kompatibel dengan importer "
        "internal proyek. Validasi terhadap template/file import Coretax resmi "
        "tetap diperlukan sebelum file diberi label siap upload ke Coretax."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
