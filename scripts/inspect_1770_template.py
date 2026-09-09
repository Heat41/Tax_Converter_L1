from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_pdf_field_map import expected_acroform_fields
from core.legacy_pdf_template import Legacy1770TemplateManager
from core.pdf_form_inspector import PdfFormInspector


def main() -> int:
    manager = Legacy1770TemplateManager()
    try:
        info = manager.require_ready()
    except Exception as exc:
        print(f"Template belum siap: {exc}")
        return 2

    inspector = PdfFormInspector()
    fields = inspector.inspect(info.path)
    expected = expected_acroform_fields()
    missing = sorted(expected - set(fields))

    print(f"Template: {info.path}")
    print(f"Halaman: {info.page_count}")
    print(f"Total field AcroForm: {len(fields)}")
    print(f"SHA256: {info.sha256}")
    print("Halaman export Bahasa Indonesia: 10, 12, 13, 14, 15")

    if missing:
        print("\nField minimum yang belum ditemukan:")
        for name in missing:
            print(f"- {name}")
        return 2

    print("\nOK - field minimum Stage 8C tersedia.")
    for page in Legacy1770TemplateManager.INDONESIAN_EXPORT_PAGES:
        count = sum(page in field.pages for field in fields.values())
        print(f"Halaman {page}: {count} field/widget terdeteksi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
