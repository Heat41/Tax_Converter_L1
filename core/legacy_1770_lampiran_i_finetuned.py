from __future__ import annotations

from io import BytesIO
from typing import Sequence, Tuple

from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_lampiran_i import (
    Legacy1770LampiranIService as BaseLegacy1770LampiranIService,
)


Rect = Tuple[float, float, float, float]


class Legacy1770LampiranIService(BaseLegacy1770LampiranIService):
    """Fine tuning visual Stage 8C.5 untuk master bersih enam halaman.

    Halaman 2 (Lampiran I halaman 1) memiliki geometri header yang sedikit
    berbeda dari halaman 3. Header halaman 2 memakai koordinat khusus, sedangkan
    Bagian C mempertahankan koordinat base dengan ukuran teks yang lebih mudah
    dibaca untuk hasil cetak dan multipage.
    """

    # Perbesar identitas Nama/NPWP pemberi kerja tanpa mengubah geometri sel.
    C_IDENTITY_FONT_SIZE = 5.9

    # Koordinat master Lampiran I halaman 1, origin kiri-atas.
    PAGE1_YEAR_RECT: Rect = (457.84, 23.90, 579.60, 43.82)
    PAGE1_PERIOD_START_RECT: Rect = (457.84, 56.18, 519.94, 72.74)
    PAGE1_PERIOD_END_RECT: Rect = (534.00, 56.18, 595.56, 72.74)
    PAGE1_NAME_RECT: Rect = (165.02, 141.38, 564.24, 156.62)

    # Pusat 16 kotak NPWP pada master halaman 2. Digunakan titik per digit
    # karena jarak antarkelompok tidak seragam.
    PAGE1_NPWP_POINTS: Sequence[Tuple[float, float]] = (
        (172.98, 128.84),
        (188.94, 128.84),
        (204.90, 128.84),
        (220.86, 128.84),
        (252.77, 128.84),
        (268.73, 128.84),
        (284.69, 128.84),
        (300.65, 128.84),
        (332.59, 128.84),
        (348.55, 128.84),
        (364.51, 128.84),
        (380.47, 128.84),
        (412.39, 128.84),
        (431.13, 128.84),
        (449.86, 128.84),
        (465.82, 128.84),
    )

    @classmethod
    def _draw_right(
        cls,
        canvas,
        rect,
        value,
        width,
        height,
        *,
        size: float = 7.0,
    ) -> None:
        """Naikkan ukuran angka Bagian C/D dengan tetap mengikuti fit sel."""
        return super()._draw_right(
            canvas,
            rect,
            value,
            width,
            height,
            size=size + 0.6,
        )

    @classmethod
    def _draw_year_at(
        cls,
        canvas,
        rect: Rect,
        year: int,
        width: float,
        height: float,
    ) -> None:
        digits = f"{int(year):04d}"[-4:]
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        cell_width = (x1 - x0) / 4.0
        sy = height / cls.BASE_HEIGHT
        font_size = 8.5 * sy
        canvas.setFont("Helvetica-Bold", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.5 * sy)
        for index, digit in enumerate(digits):
            canvas.drawCentredString(
                x0 + cell_width * (index + 0.5), baseline, digit
            )

    @classmethod
    def _draw_period_at(
        cls,
        canvas,
        rect: Rect,
        month: int,
        year: int,
        width: float,
        height: float,
    ) -> None:
        text = f"{int(month):02d}{int(year) % 100:02d}"
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        cell_width = (x1 - x0) / 4.0
        sy = height / cls.BASE_HEIGHT
        font_size = 6.0 * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.5 * sy)
        for index, digit in enumerate(text):
            canvas.drawCentredString(
                x0 + cell_width * (index + 0.5), baseline, digit
            )

    @classmethod
    def _draw_page1_npwp(
        cls,
        canvas,
        npwp: str,
        width: float,
        height: float,
    ) -> None:
        digits = [ch for ch in str(npwp or "") if ch.isdigit()][:16]
        if not digits:
            return

        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        font_size = 7.0 * sy
        canvas.setFont("Helvetica", font_size)

        box_y0_top = 121.22
        box_y1_top = 136.46
        pdf_bottom = height - (box_y1_top * sy)
        box_height = (box_y1_top - box_y0_top) * sy
        baseline = pdf_bottom + ((box_height - font_size) / 2.0) + (1.6 * sy)

        for digit, (x_top, _y_top) in zip(digits, cls.PAGE1_NPWP_POINTS):
            canvas.drawCentredString(x_top * sx, baseline, digit)

    @classmethod
    def _draw_page1_name(
        cls,
        canvas,
        name: str,
        width: float,
        height: float,
    ) -> None:
        """Cetak nama halaman 2 tanpa bergantung helper base yang berubah."""
        text = str(name or "").strip().upper()
        if not text:
            return

        x0, y0, x1, y1 = cls._pdf_rect(cls.PAGE1_NAME_RECT, width, height)
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        font_name = "Helvetica"
        size = 7.0
        max_width = (x1 - x0) - (4.0 * sx)

        while size > 5.0:
            canvas.setFont(font_name, size * sy)
            if canvas.stringWidth(text, font_name, size * sy) <= max_width:
                break
            size -= 0.2

        font_size = size * sy
        canvas.setFont(font_name, font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawString(x0 + (2.0 * sx), baseline, text)

    def _draw_page1_header(
        self,
        canvas,
        document: Legacy1770Document,
        width: float,
        height: float,
    ) -> None:
        self._draw_year_at(
            canvas,
            self.PAGE1_YEAR_RECT,
            document.tahun_pajak,
            width,
            height,
        )
        self._draw_period_at(
            canvas,
            self.PAGE1_PERIOD_START_RECT,
            1,
            document.tahun_pajak,
            width,
            height,
        )
        self._draw_period_at(
            canvas,
            self.PAGE1_PERIOD_END_RECT,
            12,
            document.tahun_pajak,
            width,
            height,
        )
        self._draw_page1_npwp(canvas, document.npwp, width, height)
        self._draw_page1_name(canvas, document.nama_wp, width, height)

    def _make_page1_overlay(self, page, document: Legacy1770Document):
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError(
                "Library reportlab diperlukan untuk mencetak Lampiran I."
            ) from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_page1_header(canvas, document, width, height)
        canvas.save()
        packet.seek(0)
        return packet