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

# Grid kecil khusus di area TK. Label angka diletakkan jauh di atas agar tidak
# menutupi kotak. Titik berjarak 4 pt sehingga mudah memilih pusat yang tepat.
POINTS = {
    "1": (218.0, 424.0),
    "2": (222.0, 424.0),
    "3": (226.0, 424.0),
    "4": (230.0, 424.0),
    "5": (234.0, 424.0),
    "6": (238.0, 424.0),
    "7": (242.0, 424.0),
    "8": (246.0, 424.0),
    "9": (250.0, 424.0),
    "10": (218.0, 428.0),
    "11": (222.0, 428.0),
    "12": (226.0, 428.0),
    "13": (230.0, 428.0),
    "14": (234.0, 428.0),
    "15": (238.0, 428.0),
    "16": (242.0, 428.0),
    "17": (246.0, 428.0),
    "18": (250.0, 428.0),
    "19": (218.0, 432.0),
    "20": (222.0, 432.0),
    "21": (226.0, 432.0),
    "22": (230.0, 432.0),
    "23": (234.0, 432.0),
    "24": (238.0, 432.0),
    "25": (242.0, 432.0),
    "26": (246.0, 432.0),
    "27": (250.0, 432.0),
}


def to_pdf_xy(x_top: float, y_top: float, width: float, height: float) -> tuple[float, float]:
    return x_top * (width / BASE_WIDTH), height - (y_top * (height / BASE_HEIGHT))


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

    # Hanya titik merah kecil. Tidak ada label di sekitar kotak PTKP.
    c.setFillColorRGB(1, 0, 0)
    c.setStrokeColorRGB(1, 0, 0)
    for label, (x_top, y_top) in POINTS.items():
        x, y = to_pdf_xy(x_top, y_top, width, height)
        c.circle(x, y, 1.2, stroke=0, fill=1)

    # Legenda ditaruh di area atas halaman agar tidak menutupi formulir PTKP.
    c.setFillColorRGB(1, 0, 0)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(36, height - 80, "DEBUG PTKP V2 - titik 1..27, pilih titik merah yang paling tepat di tengah kotak TK")
    c.setFont("Helvetica", 5.5)
    line1 = "1-9: y=424, 10-18: y=428, 19-27: y=432; x dari 218 sampai 250 naik 4 pt"
    c.drawString(36, height - 90, line1)

    c.save()
    packet.seek(0)

    overlay = PdfReader(packet).pages[0]
    page.merge_page(overlay)

    writer = PdfWriter()
    writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)

    print("Koordinat marker:")
    for label, point in POINTS.items():
        print(f"  {label:>2} = x={point[0]:.1f}, y={point[1]:.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug presisi koordinat PTKP TK pada master 1770 bersih.")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE_PATH))
    parser.add_argument(
        "--output",
        default=str(ROOT / "output" / "debug_1770_ptkp_v2.pdf"),
    )
    args = parser.parse_args()

    output = Path(args.output)
    build_debug_pdf(Path(args.template), output)
    print(f"OK - PDF debug V2 dibuat: {output}")
    print("Kirim crop area TK dan sebut NOMOR titik merah yang paling tepat di tengah kotak TK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
