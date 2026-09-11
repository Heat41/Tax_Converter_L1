from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reverse_coretax_official_package_validator import (
    OfficialCoretaxPackageValidator,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 8D.4F - validasi paket resmi Coretax "
            "(manifest, SHA-256, Excel, XML)."
        )
    )
    parser.add_argument(
        "package_dir",
        help="Folder paket hasil Stage 8D.4E.",
    )
    args = parser.parse_args()

    result = OfficialCoretaxPackageValidator().validate(
        args.package_dir
    )

    print(f"Paket       : {result.package_dir}")
    print(f"File dicek  : {len(result.checked_files)}")

    for issue in result.issues:
        category = f" [{issue.category}]" if issue.category else ""
        print(
            f"[{issue.severity}] {issue.code}{category}: {issue.message}"
        )

    if not result.ok:
        print("\nGAGAL - paket resmi Coretax tidak valid.")
        return 2

    print("\nOK - Stage 8D.4F PASS. Paket resmi Coretax konsisten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
