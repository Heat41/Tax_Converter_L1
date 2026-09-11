from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_1770_static_pdf import Legacy1770StaticPdfService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Buat PDF statis final Stage 8C.10 dari snapshot FINAL."
    )
    parser.add_argument("npwp", help="NPWP Wajib Pajak")
    parser.add_argument("tahun", type=int, help="Tahun Pajak")
    parser.add_argument(
        "--output",
        default=None,
        help="Path output PDF final.",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path master bersih 1770 enam halaman.",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    output = (
        Path(args.output)
        if args.output
        else ROOT / "output" / f"1770_FINAL_{clean_npwp}_{args.tahun}.pdf"
    )

    service = Legacy1770StaticPdfService()
    result = service.finalize_active_final(
        clean_npwp,
        args.tahun,
        output,
        template_path=args.template,
    )

    if not result.ok:
        print("GAGAL - Stage 8C.10 belum menghasilkan PDF statis yang valid.")
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    print(f"OK - PDF statis final dibuat: {result.output_path}")
    print(f"Halaman : {result.page_count}")
    print(f"Ukuran  : {result.size_bytes} bytes")
    print(f"SHA256  : {result.sha256}")
    print("Status  : STATIC - tanpa AcroForm, Annots, JavaScript/OpenAction/AA")
    print(
        "Visual  : ukuran halaman dan font hasil kalibrasi 8C.4-8C.9 dipertahankan "
        "tanpa raster/downscale."
    )

    if result.warnings:
        for issue in result.warnings:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
