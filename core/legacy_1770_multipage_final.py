from __future__ import annotations

from io import BytesIO
from typing import Optional

from core.legacy_1770_multipage import (
    Legacy1770MultipageService as CoreLegacy1770MultipageService,
)
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
    - status halaman terakhir ditentukan dari page_number/page_count aktual yang
      sedang dirender, bukan hanya metadata summary tersimpan;
    - bila subtotal Lampiran II tidak dapat dihitung karena detail PPh per Bupot
      tidak tersedia/rekonsiliasi, halaman non-terakhir menampilkan '-'.
    """

    @staticmethod
    def _is_last_section_page(page_number: int, page_count: int) -> bool:
        """True hanya untuk halaman terakhir di kelompok lampiran yang sama."""
        return int(page_number) >= max(1, int(page_count))

    @classmethod
    def _display_value_for_summary(cls, summary: MultipagePageSummary) -> Optional[float]:
        # Jangan pernah menentukan halaman terakhir dari urutan fisik PDF/master.
        # Gunakan nomor halaman kelompok lampiran (mis. Lampiran-I 4 dari 4).
        if cls._is_last_section_page(summary.page_number, summary.page_count):
            return float(summary.grand_total or 0)
        if summary.subtotal_available and summary.subtotal is not None:
            return float(summary.subtotal)
        return None

    @staticmethod
    def _with_actual_page_metadata(
        summary: MultipagePageSummary,
        page_number: int,
        page_count: int,
    ) -> MultipagePageSummary:
        """Kunci metadata summary ke nomor halaman yang benar-benar dirender."""
        return MultipagePageSummary(
            section=summary.section,
            page_number=int(page_number),
            page_count=max(1, int(page_count)),
            subtotal=summary.subtotal,
            grand_total=summary.grand_total,
            subtotal_available=summary.subtotal_available,
        )

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

        # Bersihkan angka yang mungkin sudah dicetak renderer lampiran lalu
        # pulihkan latar kuning sel jumlah. Footer tidak disentuh di sini.
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

        # Satu nilai saja. Non-terakhir = subtotal; terakhir = grand total.
        # Font dinaikkan sedikit agar tetap terbaca ketika seluruh halaman dicetak.
        max_width = max(1.0, (x1 - x0) - (6.0 * sx))
        size = 7.0
        while size > 4.4:
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

    def _make_footer_overlay(
        self,
        page,
        page_number: int,
        page_count: int,
        page_box: Rect,
        total_box: Rect,
        *,
        clear_total_rect: Optional[Rect] = None,
        draw_dash: bool = False,
    ) -> BytesIO:
        """Render nomor halaman + jumlah dengan metadata halaman aktual.

        Pemanggilan langsung ke renderer core menghindari summary ganda dari
        layer fine-tuned. Dengan demikian halaman N dari N selalu memakai grand
        total walaupun metadata cached sebelumnya berbeda.
        """
        base_stream = CoreLegacy1770MultipageService._make_footer_overlay(
            page,
            page_number,
            page_count,
            page_box,
            total_box,
            clear_total_rect=None,
            draw_dash=False,
        )

        section = self._section_from_page_box(page_box)
        if section is None:
            return base_stream

        summary = self._summary_for(section, page_number)
        if summary is None:
            return base_stream
        summary = self._with_actual_page_metadata(summary, page_number, page_count)

        from pypdf import PdfReader, PdfWriter

        base_page = PdfReader(base_stream).pages[0]
        summary_page = PdfReader(
            self._make_summary_overlay(
                page,
                section,
                summary,
                cleared_total_rect=clear_total_rect,
            )
        ).pages[0]
        base_page.merge_page(summary_page)

        packet = BytesIO()
        writer = PdfWriter()
        writer.add_page(base_page)
        writer.write(packet)
        packet.seek(0)
        return packet