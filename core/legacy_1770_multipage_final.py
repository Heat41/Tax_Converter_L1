from __future__ import annotations

from io import BytesIO
from typing import Optional

from core.legacy_1770_multipage_finetuned import (
    Legacy1770MultipageService as BaseLegacy1770MultipageService,
    MultipagePageSummary,
    Rect,
)


class Legacy1770MultipageService(BaseLegacy1770MultipageService):
    """Finalisasi visual Stage 8C.9.

    Aturan sel jumlah multipage:
    - halaman sebelum halaman terakhir hanya menampilkan subtotal halaman itu;
    - halaman terakhir hanya menampilkan total keseluruhan bagian/lampiran;
    - tidak ada label "Hal"/"Total" dan tidak ada catatan subtotal di footer;
    - bila subtotal Lampiran II tidak dapat dihitung karena detail PPh per Bupot
      tidak tersedia/rekonsiliasi, halaman non-terakhir menampilkan '-'.
    """

    @classmethod
    def _display_value_for_summary(cls, summary: MultipagePageSummary) -> Optional[float]:
        if summary.page_number >= summary.page_count:
            return float(summary.grand_total or 0)
        if summary.subtotal_available and summary.subtotal is not None:
            return float(summary.subtotal)
        return None

    def _make_summary_overlay(
        self,
        page,
        section: str,
        summary: MultipagePageSummary,
        *,
        cleared_total_rect: Optional[Rect],
    ) -> BytesIO:
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError(
                "Library reportlab diperlukan untuk Stage 8C.9."
            ) from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        sx = width / self.BASE_WIDTH
        sy = height / self.BASE_HEIGHT

        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        total_rect = self._total_rect_for(section)
        x0, y0, x1, y1 = self._pdf_rect(total_rect, width, height)

        # Bersihkan angka yang sudah dicetak renderer lampiran lalu pulihkan
        # latar kuning sel jumlah. Footer tidak disentuh di sini.
        canvas.setFillColor(Color(1.0, 1.0, 0.60))
        canvas.rect(
            x0 + (0.7 * sx),
            y0 + (0.7 * sy),
            max(0.0, (x1 - x0) - (1.4 * sx)),
            max(0.0, (y1 - y0) - (1.4 * sy)),
            stroke=0,
            fill=1,
        )
        canvas.setFillColorRGB(0, 0, 0)

        display_value = self._display_value_for_summary(summary)
        text = self._money(display_value) if display_value is not None else "-"

        # Satu nilai saja pada sel jumlah. Halaman non-terakhir = subtotal;
        # halaman terakhir = grand total keseluruhan.
        max_width = max(1.0, (x1 - x0) - (6.0 * sx))
        size = 6.2
        while size > 4.0:
            canvas.setFont("Helvetica", size * sy)
            if canvas.stringWidth(text, "Helvetica", size * sy) <= max_width:
                break
            size -= 0.2

        font_size = size * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.5 * sy)
        canvas.drawRightString(x1 - (3.0 * sx), baseline, text)

        canvas.save()
        packet.seek(0)
        return packet
