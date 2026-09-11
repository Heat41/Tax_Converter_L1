from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_mapping import (
    CATEGORY_ORDER,
    ReverseCoretaxMappingService,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview Stage 8D.1: mapping snapshot FINAL ke 6 kelompok Coretax L-1."
    )
    parser.add_argument("npwp")
    parser.add_argument("tahun", type=int)
    parser.add_argument(
        "--output",
        default=None,
        help="Opsional: simpan preview JSON.",
    )
    args = parser.parse_args()

    package = ReverseCoretaxMappingService().build_active_final(
        args.npwp,
        args.tahun,
    )

    print(f"NPWP       : {package.npwp or '-'}")
    print(f"Nama WP    : {package.nama_wp or '-'}")
    print(f"Tahun Pajak: {package.tahun_pajak or '-'}")
    print(f"Revision   : {package.revision or '-'}")
    print(f"Total baris: {package.total_rows}")
    print("")
    for category in CATEGORY_ORDER:
        print(f"{category:10}: {len(package.rows_by_category[category])} baris")

    for issue in package.issues:
        print(f"[{issue.severity}] {issue.code}: {issue.message}")

    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "npwp": package.npwp,
            "nama_wp": package.nama_wp,
            "tahun_pajak": package.tahun_pajak,
            "revision": package.revision,
            "snapshot_hash": package.snapshot_hash,
            "rows_by_category": {
                category: [asdict(row) for row in package.rows_by_category[category]]
                for category in CATEGORY_ORDER
            },
            "issues": [asdict(issue) for issue in package.issues],
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Preview JSON: {target}")

    return 0 if package.can_export else 2


if __name__ == "__main__":
    raise SystemExit(main())
