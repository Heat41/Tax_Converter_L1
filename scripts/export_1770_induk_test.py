from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_1770 import Legacy1770DocumentService
from core.legacy_1770_induk import Legacy1770IndukService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Buat PDF uji Stage 8C.4 (Form 1770 Bahasa Indonesia) dari snapshot FINAL."
    )
    parser.add_argument("npwp", help="NPWP Wajib Pajak")
    parser.add_argument("tahun", type=int, help="Tahun Pajak")
    parser.add_argument(
        "--output",
        default=None,
        help="Path PDF output. Default: output/1770_induk_<npwp>_<tahun>.pdf",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path template resmi 1770 kosong.",
    )
    args = parser.parse_args()

    clean_npwp = "".join(ch for ch in str(args.npwp) if ch.isdigit())
    output = Path(args.output) if args.output else ROOT / "output" / f"1770_induk_{clean_npwp}_{args.tahun}.pdf"

    document = Legacy1770DocumentService().build_active_final(clean_npwp, args.tahun)
    if not document.can_export_pdf:
        print("GAGAL - snapshot FINAL tidak siap diekspor.")
        for issue in document.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    service = Legacy1770IndukService()
    mapping = service.fill_induk(document, output, template_path=args.template)

    if not mapping.can_fill:
        print("GAGAL - mapping Induk tidak dapat diisi.")
        for issue in mapping.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 3

    print(f"OK - PDF uji 1770 Bahasa Indonesia dibuat: {output}")
    print("Output hanya berisi format Bahasa Indonesia: Induk + Lampiran I, II, III, IV.")
    print(f"Field Induk diisi: {len(mapping.fields)}")
    for field_name, value in mapping.fields.items():
        print(f"  {field_name} = {value}")

    if mapping.issues:
        print("Catatan mapping:")
        for issue in mapping.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")

    print("\nBuka halaman 1 output untuk memeriksa Form 1770 Induk Bahasa Indonesia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
