from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH, Legacy1770TemplateManager


BASE_WIDTH = 612.0
BASE_HEIGHT = 936.0

# Area sekitar status PTKP pada angka 10, koordinat origin kiri-atas.
# Marker dibuat cukup menyebar supaya kita tidak perlu menebak lagi.
MARKERS = {
    "A1": (210.0, 420.0),
    "A2": (220.0, 420.0),
    "A3": (230.0, 420.0),
    "A4": (240.0, 420.0),
    "A5": (250.0, 420.0),
    "B1": (210.0, 428.0),
    "B2": (220.0, 428.0),
    "B3": (230.0, 428.0),
    "B4": (240.0, 428.0),
    "B5": (250.0, 428.0),
    "C1": (210.0, 436.0),
    "C2": (220.0, 436.0),
    "C3": (230.0, 436.0),
    "C4": (240.0, 436.0),
    "C5": (250.0, 436.0),
}


def to_pdf_xy(x_top: float, y_top: float, width: float, height: float) -> tuple[float, float]:
    sx = width / BASE_WIDTH
    sy = height / BASE_HEIGHT
    return x_top * sx, height - (y_top * sy)


def build_debug_pdf(template: Path, output: Path) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as reportlab_canvas
    except ImportError as exc:
        raise RuntimeError(
            "pypdf dan reportlab diperlukan. Install dengan: python -m pip install pypdf reportlab"
        ) from exc

    manager = Legacy1770TemplateManager(template)
    info = manager.require_ready()
    reader = PdfReader(str(info.path))
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)

    packet = BytesIO()
    c = reportlab_canvas.Canvas(packet, pagesize=(width, height))

    # Judul debug di area kosong atas agar tidak mengganggu kotak PTKP.
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, height - 84, "DEBUG PTKP - pilih marker yang tepat di tengah kotak TK")

    for label, (x_top, y_top) in MARKERS.items():
        x, y = to_pdf_xy(x_top, y_top, width, height)
        # Crosshair merah + label kecil. Hanya untuk file debug.
        c.setStrokeColorRGB(1, 0, 0)
        c.setFillColorRGB(1, 0, 0)
        c.setLineWidth(0.6)
        c.line(x - 3, y, x + 3, y)
        c.line(x, y - 3, x, y + 3)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(x + 3.5, y + 2.0, label)

    c.save()
    packet.seek(0)

    overlay = PdfReader(packet).pages[0]
    page.merge_page(overlay)

    writer = PdfWriter()
    writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Buat PDF debug koordinat PTKP pada halaman Induk 1770.")
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path master bersih 1770 6 halaman.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "output" / "debug_1770_ptkp.pdf"),
        help="Path output PDF debug.",
    )
    args = parser.parse_args()

    template = Path(args.template)
    output = Path(args.output)
    build_debug_pdf(template, output)

    print(f"OK - PDF debug dibuat: {output}")
    print("Buka area TK/K/K-I pada angka 10.")
    print("Kirim screenshot crop dan sebut marker mana yang tepat di tengah kotak TK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
