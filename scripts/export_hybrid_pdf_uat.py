from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.legacy_1770_static_pdf import Legacy1770StaticPdfService


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UAT output PDF HYBRID 1770 dari snapshot FINAL."
    )
    parser.add_argument("--npwp", required=True, help="NPWP/NIK WP FINAL")
    parser.add_argument("--year", required=True, type=int, help="Tahun Pajak")
    parser.add_argument(
        "--output",
        default="",
        help="Path PDF output; default dibuat di folder output/.",
    )
    args = parser.parse_args()

    npwp = _digits(args.npwp)
    output = Path(args.output) if args.output else (
        PROJECT_ROOT / "output" / f"1770_hybrid_{npwp}_{args.year}.pdf"
    )

    result = Legacy1770StaticPdfService().finalize_active_final(
        npwp,
        args.year,
        output,
    )

    print("=" * 68)
    print("UAT PDF HYBRID 1770")
    print("=" * 68)
    print(f"NPWP       : {npwp}")
    print(f"Tahun      : {args.year}")
    print(f"Output     : {result.output_path}")
    print(f"Halaman    : {result.page_count}")
    print(f"Ukuran     : {result.size_bytes:,} byte")
    print(f"SHA256     : {result.sha256 or '-'}")

    if result.issues:
        print("\nIssues:")
        for issue in result.issues:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")

    if not result.ok:
        print("\n[FAIL] PDF HYBRID belum lolos validasi.")
        return 1

    from pypdf import PdfReader

    reader = PdfReader(str(result.output_path))
    legal_ok = True
    for index, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        page_ok = abs(width - 612.0) <= 2.0 and abs(height - 936.0) <= 2.0
        legal_ok = legal_ok and page_ok
        print(
            f"Halaman {index:02d}: {width:.1f} x {height:.1f} "
            f"{'[LEGAL]' if page_ok else '[BUKAN LEGAL]'}"
        )

    page1 = reader.pages[0].extract_text() or "" if reader.pages else ""
    page2 = reader.pages[1].extract_text() or "" if len(reader.pages) > 1 else ""
    h1_ok = "HALAMAN 1" in page1 and "INDUK" in page1
    h2_ok = "HALAMAN 2" in page2 and "INDUK" in page2

    print("\nBoundary HYBRID:")
    print(f"  01 Induk H1 format baru : {'PASS' if h1_ok else 'CHECK'}")
    print(f"  02 Induk H2 format baru : {'PASS' if h2_ok else 'CHECK'}")
    print("  03 dst format lama      : cek visual Lampiran I H2, II, III, IV")

    if not legal_ok or not h1_ok or not h2_ok:
        print("\n[FAIL] Ada pemeriksaan dasar yang belum lolos.")
        return 1

    print("\n[PASS] Struktur dasar PDF HYBRID lolos UAT otomatis.")
    print("Buka PDF dan lakukan pemeriksaan visual halaman 03 sampai akhir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
