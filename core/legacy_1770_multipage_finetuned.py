from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_lampiran_i import LampiranIMappingResult
from core.legacy_1770_lampiran_i_finetuned import Legacy1770LampiranIService
from core.legacy_1770_lampiran_ii import LampiranIIMappingResult
from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService
from core.legacy_1770_lampiran_iv import LampiranIVMappingResult, Legacy1770LampiranIVService
from core.legacy_1770_multipage import (
    Legacy1770MultipageService as BaseLegacy1770MultipageService,
)


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class MultipagePageSummary:
    section: str
    page_number: int
    page_count: int
    subtotal: Optional[float]
    grand_total: float
    subtotal_available: bool = True


class Legacy1770MultipageService(BaseLegacy1770MultipageService):
    """Penyempurnaan Stage 8C.9: subtotal halaman + total keseluruhan.

    Aturan output:
    - setiap halaman kelompok multipage menampilkan catatan subtotal halaman dan
      total keseluruhan;
    - pada halaman non-terakhir, sel jumlah utama menampilkan subtotal halaman;
    - pada halaman terakhir, sel jumlah utama tetap menampilkan grand total resmi;
    - Lampiran II tidak pernah membagi Kredit Pajak FINAL secara proporsional.
      Jika detail PPh per Bupot belum tersedia/rekonsiliasi, subtotal halaman
      ditampilkan sebagai '-' dan grand total FINAL tetap dicetak apa adanya.
    """

    # Catatan ditempatkan dekat footer masing-masing master. Posisi sengaja
    # berdiri sendiri karena geometri tiap halaman berbeda.
    L1_SUMMARY_RECT: Rect = (255.0, 832.0, 590.0, 844.0)
    L2_SUMMARY_RECT: Rect = (250.0, 844.0, 590.0, 856.0)
    L4_SUMMARY_RECT: Rect = (250.0, 751.0, 580.0, 765.0)

    def __init__(self) -> None:
        super().__init__()
        self._page_summaries: Dict[str, List[MultipagePageSummary]] = {}

    @staticmethod
    def _chunks(rows: Sequence, size: int) -> List[Sequence]:
        if not rows:
            return [rows[0:0]]
        return [rows[start : start + size] for start in range(0, len(rows), size)]

    @staticmethod
    def _money(value: float) -> str:
        number = int(round(float(value or 0)))
        return ("-" if number < 0 else "") + f"{abs(number):,}".replace(",", ".")

    def build_page_summaries(
        self, document: Legacy1770Document
    ) -> Dict[str, List[MultipagePageSummary]]:
        l1_service = Legacy1770LampiranIService()
        l2_service = Legacy1770LampiranIIService()
        l4_service = Legacy1770LampiranIVService()

        l1 = l1_service.map_document(document)
        l2 = l2_service.map_document(document)
        l4 = l4_service.map_document(document)

        result: Dict[str, List[MultipagePageSummary]] = {"L1": [], "L2": [], "L4": []}

        l1_chunks = self._chunks(l1.employment_rows, l1_service.MAX_EMPLOYMENT_ROWS)
        for index, rows in enumerate(l1_chunks, start=1):
            result["L1"].append(
                MultipagePageSummary(
                    section="L1",
                    page_number=index,
                    page_count=len(l1_chunks),
                    subtotal=sum(float(row.netto or 0) for row in rows),
                    grand_total=float(l1.jumlah_bagian_c or 0),
                    subtotal_available=True,
                )
            )

        l2_chunks = self._chunks(l2.rows, l2_service.MAX_ROWS)
        l2_detail_total = sum(float(row.pph_dipotong or 0) for row in l2.rows)
        l2_grand_total = float(l2.jumlah_bagian_a or 0)
        # Detail dianggap cukup untuk subtotal hanya bila jumlah seluruh detail
        # merekonsiliasi grand total. Ini mencegah pembagian Kredit Pajak FINAL
        # secara buatan saat PPh per Bupot belum tersedia.
        l2_detail_available = (
            abs(l2_detail_total - l2_grand_total) <= 1.0
            or (abs(l2_detail_total) <= 1.0 and abs(l2_grand_total) <= 1.0)
        )
        for index, rows in enumerate(l2_chunks, start=1):
            result["L2"].append(
                MultipagePageSummary(
                    section="L2",
                    page_number=index,
                    page_count=len(l2_chunks),
                    subtotal=(
                        sum(float(row.pph_dipotong or 0) for row in rows)
                        if l2_detail_available
                        else None
                    ),
                    grand_total=l2_grand_total,
                    subtotal_available=l2_detail_available,
                )
            )

        l4_chunks = self._chunks(l4.harta_rows, l4_service.MAX_HARTA_ROWS)
        for index, rows in enumerate(l4_chunks, start=1):
            result["L4"].append(
                MultipagePageSummary(
                    section="L4",
                    page_number=index,
                    page_count=len(l4_chunks),
                    subtotal=sum(float(row.harga_perolehan or 0) for row in rows),
                    grand_total=float(l4.jumlah_bagian_a or 0),
                    subtotal_available=True,
                )
            )

        return result

    def _section_from_page_box(self, page_box: Rect) -> Optional[str]:
        if tuple(page_box) == tuple(self.L1_PAGE_BOX):
            return "L1"
        if tuple(page_box) == tuple(self.L2_PAGE_BOX):
            return "L2"
        if tuple(page_box) == tuple(self.L4_PAGE_BOX):
            return "L4"
        return None

    def _summary_for(self, section: str, page_number: int) -> Optional[MultipagePageSummary]:
        pages = self._page_summaries.get(section) or []
        index = int(page_number) - 1
        if 0 <= index < len(pages):
            return pages[index]
        return None

    def _summary_rect_for(self, section: str) -> Rect:
        if section == "L1":
            return self.L1_SUMMARY_RECT
        if section == "L2":
            return self.L2_SUMMARY_RECT
        return self.L4_SUMMARY_RECT

    def _section_label(self, section: str) -> str:
        if section == "L1":
            return "Bagian C"
        if section == "L2":
            return "Bagian A"
        return "Bagian A"

    def _make_summary_overlay(
        self,
        page,
        section: str,
        summary: MultipagePageSummary,
        *,
        cleared_total_rect: Optional[Rect],
    ) -> BytesIO:
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk Stage 8C.9.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        sx = width / self.BASE_WIDTH
        sy = height / self.BASE_HEIGHT
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        # Pada halaman dasar yang sudah di-mask oleh renderer multipage, tulis
        # subtotal halaman. Untuk Lampiran II yang detailnya belum ada, tulis '-'.
        if cleared_total_rect is not None:
            x0, y0, x1, y1 = self._pdf_rect(cleared_total_rect, width, height)
            if summary.subtotal_available and summary.subtotal is not None:
                text = self._money(summary.subtotal)
                canvas.setFont("Helvetica", 6.2 * sy)
                baseline = y0 + ((y1 - y0 - (6.2 * sy)) / 2.0) + (1.6 * sy)
                canvas.drawRightString(x1 - (3.0 * sx), baseline, text)
            else:
                canvas.setFont("Helvetica", 6.2 * sy)
                canvas.drawRightString(
                    x1 - (3.0 * sx),
                    y0 + ((y1 - y0) / 2.0) - (1.0 * sy),
                    "-",
                )

        label = self._section_label(section)
        if summary.subtotal_available and summary.subtotal is not None:
            subtotal_text = f"Rp {self._money(summary.subtotal)}"
        else:
            subtotal_text = "- (detail belum tersedia)"
        note = (
            f"Subtotal halaman: {subtotal_text}   |   "
            f"Total {label}: Rp {self._money(summary.grand_total)}"
        )

        x0, y0, x1, y1 = self._pdf_rect(self._summary_rect_for(section), width, height)
        size = 5.0
        while size > 3.6:
            canvas.setFont("Helvetica-Bold", size * sy)
            if canvas.stringWidth(note, "Helvetica-Bold", size * sy) <= (x1 - x0):
                break
            size -= 0.2
        font_size = size * sy
        canvas.setFont("Helvetica-Bold", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.4 * sy)
        canvas.drawRightString(x1, baseline, note)

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
        # Gunakan footer base untuk nomor halaman dan masking, tetapi dash lama
        # dimatikan karena sel non-terakhir sekarang berisi subtotal halaman.
        base_stream = BaseLegacy1770MultipageService._make_footer_overlay(
            page,
            page_number,
            page_count,
            page_box,
            total_box,
            clear_total_rect=clear_total_rect,
            draw_dash=False,
        )

        section = self._section_from_page_box(page_box)
        if section is None:
            return base_stream
        summary = self._summary_for(section, page_number)
        if summary is None:
            return base_stream

        # Gabungkan footer base dan ringkasan dalam satu stream agar caller hanya
        # perlu satu merge ke halaman target.
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

    def _build_l1_continuation(
        self,
        template_page,
        document: Legacy1770Document,
        rows: Sequence,
        grand_total: float,
        page_number: int,
        page_count: int,
        *,
        is_last: bool,
    ):
        page = deepcopy(template_page)
        service = Legacy1770LampiranIService()
        subtotal = sum(float(row.netto or 0) for row in rows)
        mapping = LampiranIMappingResult(
            employment_rows=list(rows),
            jumlah_bagian_c=float(grand_total if is_last else subtotal),
            jumlah_bagian_d=0.0,
        )
        self._merge_stream(page, service._make_page2_overlay(page, document, mapping))
        self._merge_stream(
            page,
            self._make_footer_overlay(
                page,
                page_number,
                page_count,
                self.L1_PAGE_BOX,
                self.L1_TOTAL_BOX,
            ),
        )
        self._sanitize_page(page)
        return page

    def _build_l2_continuation(
        self,
        template_page,
        document: Legacy1770Document,
        rows: Sequence,
        grand_total: float,
        page_number: int,
        page_count: int,
        *,
        is_last: bool,
    ):
        page = deepcopy(template_page)
        service = Legacy1770LampiranIIService()
        summary = self._summary_for("L2", page_number)
        subtotal = (
            float(summary.subtotal or 0)
            if summary is not None and summary.subtotal_available
            else 0.0
        )
        display_total = float(grand_total if is_last else subtotal)
        mapping = LampiranIIMappingResult(
            rows=list(rows),
            jumlah_bagian_a=display_total,
            detail_pph_total=sum(float(row.pph_dipotong or 0) for row in rows),
        )
        self._merge_stream(page, service._make_overlay(page, document, mapping))
        self._merge_stream(
            page,
            self._make_footer_overlay(
                page,
                page_number,
                page_count,
                self.L2_PAGE_BOX,
                self.L2_TOTAL_BOX,
            ),
        )
        self._sanitize_page(page)
        return page

    def _build_l4_continuation(
        self,
        template_page,
        document: Legacy1770Document,
        rows: Sequence,
        grand_total: float,
        page_number: int,
        page_count: int,
        *,
        is_last: bool,
    ):
        page = deepcopy(template_page)
        service = Legacy1770LampiranIVService()
        subtotal = sum(float(row.harga_perolehan or 0) for row in rows)
        mapping = LampiranIVMappingResult(
            harta_rows=list(rows),
            jumlah_bagian_a=float(grand_total if is_last else subtotal),
        )
        self._merge_stream(page, service._make_overlay(page, document, mapping))
        self._merge_stream(
            page,
            self._make_footer_overlay(
                page,
                page_number,
                page_count,
                self.L4_PAGE_BOX,
                self.L4_TOTAL_BOX,
            ),
        )
        self._sanitize_page(page)
        return page

    def fill_multipage(self, document, output_path, *, template_path=None):
        self._page_summaries = self.build_page_summaries(document)
        try:
            return super().fill_multipage(
                document,
                output_path,
                template_path=template_path,
            )
        finally:
            # Tidak menyimpan data WP di instance setelah ekspor selesai.
            self._page_summaries = {}
