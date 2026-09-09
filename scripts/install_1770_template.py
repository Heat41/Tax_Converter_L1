from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH, Legacy1770TemplateManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Pasang template PDF 1770 kosong resmi DJP.")
    parser.add_argument("--source", required=True, help="Path PDF 1770 kosong")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_file():
        print(f"File sumber tidak ditemukan: {source}")
        return 2
    if source.suffix.lower() != ".pdf":
        print("File sumber harus PDF.")
        return 2

    target = DEFAULT_TEMPLATE_PATH
    manager = Legacy1770TemplateManager(source)
    try:
        info = manager.require_ready()
    except Exception as exc:
        print(f"Template tidak valid: {exc}")
        return 2

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    installed = Legacy1770TemplateManager(target).require_ready()

    print(f"Template berhasil dipasang: {installed.path}")
    print(f"Halaman: {installed.page_count}")
    print(f"Ukuran: {installed.size_bytes} byte")
    print(f"SHA256: {installed.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
