from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_pdf_template import Legacy1770TemplateManager


def main() -> int:
    manager = Legacy1770TemplateManager()
    try:
        info = manager.require_ready()
    except Exception as exc:
        print(f"Template belum siap: {exc}")
        return 2

    print(f"Template: {info.path}")
    print(f"Halaman: {info.page_count}")
    print(f"Ukuran: {info.size_bytes} byte")
    print(f"SHA256: {info.sha256}")
    print("Urutan halaman produksi:")
    print("  1 = Induk")
    print("  2 = Lampiran I halaman 1")
    print("  3 = Lampiran I halaman 2")
    print("  4 = Lampiran II")
    print("  5 = Lampiran III")
    print("  6 = Lampiran IV")
    print("\nOK - master visual Stage 8C siap digunakan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
