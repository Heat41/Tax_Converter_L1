from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_1770 import Legacy1770DocumentService
from core.legacy_1770_lampiran_ii import Legacy1770LampiranIIService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Buat PDF uji Stage 8C.6 (Induk + Lampiran I + Lampiran II) dari snapshot FINAL."
    )
    parser.add_argument("npwp", help="NPWP Wajib Pajak")
    parser.add_argument("tahun", type=int, help="Tahun Pajak")
    parser.add_argument(
        "--output",
        default=None,
        help="Path PDF output. Default: output/1770_lampiran_ii_<npwp>_<tahun>.pdf",
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
        else ROOT / "output" / f"1770_lampiran_ii_{clean_npwp}_{args.tahun}.pdf"
    )

    document = Legacy1770DocumentService().build_active_final(clean_npwp, args.tahun)
    if not document.can_export_pdf:
        print("GAGAL - snapshot FINAL tidak siap diekspor.")
        for issue in document.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 2

    service = Legacy1770LampiranIIService()
    mapping = service.fill_lampiran_ii(document, output, template_path=args.template)
    if not mapping.can_fill:
        print("GAGAL - Lampiran II tidak dapat dibentuk.")
        for issue in mapping.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 3

    print(f"OK - PDF uji Stage 8C.6 dibuat: {output}")
    print("Halaman 1 = Induk")
    print("Halaman 2-3 = Lampiran I")
    print("Halaman 4 = Lampiran II")
    print(f"Baris Bupot tersedia: {len(mapping.rows)}")
    print(f"Baris tercetak pada halaman 4: {min(len(mapping.rows), service.MAX_ROWS)}")
    print(f"Total PPh detail tersedia: {int(round(mapping.detail_pph_total))}")
    print(f"JBA / Kredit Pajak FINAL: {int(round(mapping.jumlah_bagian_a))}")

    if mapping.issues:
        print("Catatan Lampiran II:")
        for issue in mapping.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")

    print("\nBuka halaman 4 untuk pemeriksaan visual Stage 8C.6.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
