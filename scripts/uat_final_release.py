from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import CORETAX_TEMPLATE_DIR
from core.final_uat import FinalUatService


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8E.1 - Final UAT end-to-end dari snapshot FINAL "
            "ke Format Lama dan Paket Coretax."
        )
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--template-dir",
        default=str(CORETAX_TEMPLATE_DIR),
        help=(
            "Folder template Coretax resmi. Default memakai resource bawaan "
            "resources/templates/coretax."
        ),
    )
    parser.add_argument(
        "--source-dir",
        default=None,
        help=(
            "Opsional. Folder sumber Coretax asli untuk rekonsiliasi fisik."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Folder output UAT. Default: "
            "output/uat_<npwp>_<tahun>"
        ),
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Opsional. Path database SQLite yang akan diuji.",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT / "output" / f"uat_{clean_npwp}_{args.tahun}"
    )

    result = FinalUatService(
        db_path=args.db_path
    ).run(
        clean_npwp,
        args.tahun,
        template_dir=args.template_dir,
        source_dir=args.source_dir,
        output_dir=output_dir,
    )

    print("=" * 78)
    print("FINAL UAT - TAX CONVERTER L-1")
    print("=" * 78)
    print(f"NPWP            : {result.npwp}")
    print(f"Tahun Pajak     : {result.tahun_pajak}")
    print(f"Revision FINAL  : {result.revision}")
    print(f"Kategori aktif  : {', '.join(result.active_categories) or '-'}")
    print(f"Total Harta     : {result.total_rows} baris")
    print("")

    for item in result.checkpoints:
        print(f"[{item.status}] {item.code} - {item.label}")
        if item.detail:
            print(f"       {item.detail}")

    print("")
    print(f"Format Lama     : {result.pdf_path or '-'}")
    print(f"Paket Coretax   : {result.coretax_dir or '-'}")
    print(f"Rekonsiliasi    : {result.reconciliation_status}")
    print(f"Report JSON     : {result.output_dir / 'uat_report.json'}")
    print("")
    print("HASIL UAT       : " + ("PASS" if result.ok else "FAIL"))

    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
