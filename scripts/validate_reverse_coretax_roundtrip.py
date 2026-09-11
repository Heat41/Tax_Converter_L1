from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_mapping import CATEGORY_ORDER
from core.reverse_coretax_roundtrip import ReverseCoretaxRoundtripValidator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 8D.3 - validasi round-trip 6 file Excel reverse Coretax."
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Folder 6 file Excel hasil Stage 8D.2.",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    result = ReverseCoretaxRoundtripValidator().validate_active_final(
        clean_npwp,
        args.tahun,
        args.input_dir,
    )

    print(f"Folder     : {result.output_dir}")
    print(f"File dicek : {len(result.checked_files)}/6")
    print("")
    for category in CATEGORY_ORDER:
        expected = result.expected_counts.get(category, 0)
        actual = result.actual_counts.get(category, 0)
        state = "PASS" if expected == actual and category in result.checked_files else "FAIL"
        print(
            f"{category:10}: expected {expected:>3} | actual {actual:>3} | {state}"
        )

    for issue in result.issues:
        row_text = f" baris {issue.row_number}" if issue.row_number else ""
        print(
            f"[{issue.severity}] {issue.code} {issue.category}{row_text}: "
            f"{issue.message}"
        )

    if not result.ok:
        print("\nGAGAL - round-trip 8D.3 menemukan perbedaan.")
        return 2

    print(
        "\nOK - 8D.3 PASS. Enam file Excel dapat dibaca ulang dengan kontrak "
        "internal tanpa perubahan jumlah baris, kode harta, tahun, nilai, "
        "dan field kategori yang diekspor."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
