from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH, Legacy1770TemplateManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pasang master visual PDF 1770 lama 6 halaman Bahasa Indonesia."
    )
    parser.add_argument("--source", required=True, help="Path file PDF master 1770 6 halaman")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_file():
        print(f"File sumber tidak ditemukan: {source}")
        return 2
    if source.suffix.lower() != ".pdf":
        print("File sumber harus PDF.")
        return 2

    manager = Legacy1770TemplateManager(source)
    try:
        info = manager.require_ready()
    except Exception as exc:
        print(f"Template tidak valid: {exc}")
        return 2

    target = DEFAULT_TEMPLATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    installed = Legacy1770TemplateManager(target).require_ready()

    print(f"Master template berhasil dipasang: {installed.path}")
    print(f"Halaman: {installed.page_count}")
    print(f"Ukuran: {installed.size_bytes} byte")
    print(f"SHA256: {installed.sha256}")
    print("Urutan: 1 Induk, 2-3 Lampiran I, 4 Lampiran II, 5 Lampiran III, 6 Lampiran IV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
