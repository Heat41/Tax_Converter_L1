from __future__ import annotations

from io import BytesIO

from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_induk import Legacy1770IndukService as BaseLegacy1770IndukService


class Legacy1770IndukService(BaseLegacy1770IndukService):
    """Fine tuning visual Stage 8C.4 untuk master bersih 6 halaman."""

    # Posisi angka tanggungan pada baris PTKP disesuaikan ke kotak input aktual.
    PTKP_STATUS_RECTS = {
        "TK": (242.5, 418.8, 257.5, 434.7),
        "K": (284.0, 418.8, 299.0, 434.7),
        "KI": (327.0, 418.8, 342.0, 434.7),
    }

    # Checkbox Pernyataan: Wajib Pajak (bukan Kuasa).
    DECLARATION_WP_CHECK_RECT = (101.0, 848.5, 114.0, 861.5)

    def _make_induk_overlay(self, page, document: Legacy1770Document):
        """Tambahkan polish akhir tanpa mengubah mapping/perhitungan induk."""
        base_stream = super()._make_induk_overlay(page, document)

        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf dan reportlab diperlukan untuk fine tuning Form 1770."
            ) from exc

        base_page = PdfReader(base_stream).pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        packet = BytesIO()
        c = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        # Pernyataan atas nama Wajib Pajak sendiri. Kuasa tetap kosong.
        self._draw_center(
            c,
            self.DECLARATION_WP_CHECK_RECT,
            "X",
            width,
            height,
            font_size=7.0,
            bold=True,
        )

        c.save()
        packet.seek(0)
        polish_page = PdfReader(packet).pages[0]
        base_page.merge_page(polish_page)

        writer = PdfWriter()
        writer.add_page(base_page)
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return output
