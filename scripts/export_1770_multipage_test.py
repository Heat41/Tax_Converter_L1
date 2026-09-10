from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_1770 import Legacy1770DocumentService
from core.legacy_1770_multipage_final import Legacy1770MultipageService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Buat PDF uji Stage 8C.9 multipage dari snapshot FINAL."
    )
    parser.add_argument("npwp", help="NPWP Wajib Pajak")
    parser.add_argument("tahun", type=int, help="Tahun Pajak")
    parser.add_argument(
        "--output",
        default=None,
        help="Path PDF output. Default: output/1770_multipage_<npwp>_<tahun>.pdf",
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
        else ROOT / "output" / f"1770_multipage_{clean_npwp}_{args.tahun}.pdf"
    )

    document = Legacy1770DocumentService().build_active_final(clean_npwp, args.tahun)
    if not document.can_export_pdf:
        print("GAGAL - snapshot FINAL tidak siap diekspor.")
        for issue in document.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    service = Legacy1770MultipageService()
    summaries = service.build_page_summaries(document)
    plan = service.fill_multipage(document, output, template_path=args.template)
    errors = [issue for issue in plan.issues if issue.severity == "ERROR"]
    if errors:
        print("GAGAL - Stage 8C.9 multipage tidak dapat dibentuk.")
        for issue in plan.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 3

    print(f"OK - PDF uji Stage 8C.9 dibuat: {output}")
    print(f"Total halaman output: {plan.output_pages}")
    print(
        f"Lampiran I Bagian C: {plan.employment_rows} baris -> "
        f"{plan.lampiran_i_c_pages} halaman tipe Lampiran I-2"
    )
    print(
        f"Lampiran II: {plan.lampiran_ii_rows} baris -> "
        f"{plan.lampiran_ii_pages} halaman"
    )
    print(
        f"Lampiran IV Harta: {plan.harta_rows} baris -> "
        f"{plan.lampiran_iv_pages} halaman"
    )
    print(f"Halaman tambahan: {plan.extra_pages}")

    print("\nRingkasan nilai per halaman:")
    for section, pages in summaries.items():
        for page in pages:
            if page.page_number == page.page_count:
                displayed = f"{int(round(page.grand_total)):,}".replace(",", ".")
                kind = "total keseluruhan"
            elif page.subtotal_available and page.subtotal is not None:
                displayed = f"{int(round(page.subtotal)):,}".replace(",", ".")
                kind = "subtotal halaman"
            else:
                displayed = "-"
                kind = "subtotal tidak tersedia"
            print(
                f"  {section} halaman {page.page_number}/{page.page_count}: "
                f"{kind}={displayed}"
            )

    if plan.issues:
        print("Catatan multipage:")
        for issue in plan.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")

    print(
        "\nPeriksa footer 'Halaman ke/dari'. Halaman sebelum terakhir harus "
        "menampilkan subtotal halaman, sedangkan halaman terakhir hanya total keseluruhan."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
