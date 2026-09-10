from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_lampiran_i import LampiranIMappingResult
from core.legacy_1770_lampiran_i_finetuned import Legacy1770LampiranIService
from core.legacy_1770_lampiran_ii import LampiranIIMappingResult
from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService
from core.legacy_1770_lampiran_iv import LampiranIVMappingResult, Legacy1770LampiranIVService


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class MultipageIssue:
    code: str
    severity: str
    message: str


@dataclass
class MultipagePlan:
    lampiran_i_c_pages: int = 1
    lampiran_ii_pages: int = 1
    lampiran_iv_pages: int = 1
    employment_rows: int = 0
    lampiran_ii_rows: int = 0
    harta_rows: int = 0
    issues: List[MultipageIssue] = field(default_factory=list)

    @property
    def extra_pages(self) -> int:
        return (
            max(0, self.lampiran_i_c_pages - 1)
            + max(0, self.lampiran_ii_pages - 1)
            + max(0, self.lampiran_iv_pages - 1)
        )

    @property
    def output_pages(self) -> int:
        return 6 + self.extra_pages


class Legacy1770MultipageService:
    """Stage 8C.9 - halaman lanjutan Lampiran I, II, dan IV.

    Strategi:
    - Enam halaman dasar tetap dibentuk oleh renderer Stage 8C.4 s.d. 8C.8.
    - Lampiran I Bagian C dipecah 6 baris per halaman tipe halaman-3.
    - Lampiran II dipecah 15 baris per halaman tipe halaman-4.
    - Lampiran IV Harta dipecah 10 baris per halaman tipe halaman-6.
    - Jika lebih dari satu halaman, total bagian hanya dicetak pada halaman
      terakhir agar tidak terlihat sebagai subtotal yang berulang.
    - Footer "Halaman ke ... dari ..." diisi untuk tiap kelompok lampiran.

    Master visual tetap sumber bentuk halaman; data selalu berasal dari snapshot
    FINAL WP aktif. Tidak ada data contoh yang ditanam di renderer.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0

    # Kotak footer pada master (origin kiri-atas), diukur per halaman karena
    # setiap lampiran memiliki geometri yang sedikit berbeda.
    L1_PAGE_BOX: Rect = (449.62, 845.76, 466.18, 863.28)
    L1_TOTAL_BOX: Rect = (482.02, 845.76, 497.86, 863.28)

    L2_PAGE_BOX: Rect = (453.28, 859.92, 470.62, 874.20)
    L2_TOTAL_BOX: Rect = (486.58, 859.92, 502.54, 874.20)

    L4_PAGE_BOX: Rect = (459.34, 768.24, 475.06, 779.40)
    L4_TOTAL_BOX: Rect = (490.66, 768.24, 506.26, 779.40)

    @staticmethod
    def _pages_for_rows(row_count: int, page_size: int) -> int:
        return max(1, int(ceil(max(0, int(row_count)) / float(page_size))))

    def build_plan(self, document: Legacy1770Document) -> MultipagePlan:
        l1 = Legacy1770LampiranIService().map_document(document)
        l2 = Legacy1770LampiranIIService().map_document(document)
        l4 = Legacy1770LampiranIVService().map_document(document)

        plan = MultipagePlan(
            lampiran_i_c_pages=self._pages_for_rows(
                len(l1.employment_rows), Legacy1770LampiranIService.MAX_EMPLOYMENT_ROWS
            ),
            lampiran_ii_pages=self._pages_for_rows(
                len(l2.rows), Legacy1770LampiranIIService.MAX_ROWS
            ),
            lampiran_iv_pages=self._pages_for_rows(
                len(l4.harta_rows), Legacy1770LampiranIVService.MAX_HARTA_ROWS
            ),
            employment_rows=len(l1.employment_rows),
            lampiran_ii_rows=len(l2.rows),
            harta_rows=len(l4.harta_rows),
        )

        if plan.extra_pages:
            plan.issues.append(
                MultipageIssue(
                    "MP_INFO",
                    "INFO",
                    f"Output membutuhkan {plan.extra_pages} halaman lanjutan; total menjadi {plan.output_pages} halaman.",
                )
            )
        return plan

    @classmethod
    def _pdf_rect(cls, rect: Rect, width: float, height: float) -> Rect:
        x0, y0, x1, y1 = rect
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        return x0 * sx, height - y1 * sy, x1 * sx, height - y0 * sy

    @classmethod
    def _draw_box_text(
        cls,
        canvas,
        rect: Rect,
        text: str,
        width: float,
        height: float,
    ) -> None:
        value = str(text or "")
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        size = 7.0
        while size > 4.6:
            canvas.setFont("Helvetica", size * sy)
            if canvas.stringWidth(value, "Helvetica", size * sy) <= (x1 - x0) - 2.0:
                break
            size -= 0.2
        font_size = size * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.5 * sy)
        canvas.drawCentredString((x0 + x1) / 2.0, baseline, value)

    @classmethod
    def _make_footer_overlay(
        cls,
        page,
        page_number: int,
        page_count: int,
        page_box: Rect,
        total_box: Rect,
        *,
        clear_total_rect: Optional[Rect] = None,
        draw_dash: bool = False,
    ) -> BytesIO:
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk Stage 8C.9.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        if clear_total_rect is not None:
            x0, y0, x1, y1 = cls._pdf_rect(clear_total_rect, width, height)
            canvas.setFillColor(Color(1.0, 1.0, 0.60))
            canvas.rect(x0 + 0.4, y0 + 0.4, (x1 - x0) - 0.8, (y1 - y0) - 0.8, stroke=0, fill=1)
            if draw_dash:
                canvas.setFillColorRGB(0, 0, 0)
                canvas.setFont("Helvetica", 6.2 * (height / cls.BASE_HEIGHT))
                canvas.drawRightString(x1 - 3.0, y0 + ((y1 - y0) / 2.0) - 1.0, "-")

        canvas.setFillColorRGB(0, 0, 0)
        cls._draw_box_text(canvas, page_box, str(page_number), width, height)
        cls._draw_box_text(canvas, total_box, str(page_count), width, height)
        canvas.save()
        packet.seek(0)
        return packet

    @staticmethod
    def _merge_stream(page, stream: BytesIO) -> None:
        from pypdf import PdfReader

        overlay = PdfReader(stream).pages[0]
        page.merge_page(overlay)

    @staticmethod
    def _sanitize_page(page) -> None:
        for key in ("/Annots", "/AA"):
            if key in page:
                del page[key]

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
        mapping = LampiranIMappingResult(
            employment_rows=list(rows),
            jumlah_bagian_c=float(grand_total if is_last else 0),
            # Bagian D hanya dicetak pada halaman dasar, bukan diulang pada
            # halaman lanjutan Bagian C.
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
        mapping = LampiranIIMappingResult(
            rows=list(rows),
            jumlah_bagian_a=float(grand_total if is_last else 0),
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
        mapping = LampiranIVMappingResult(
            harta_rows=list(rows),
            jumlah_bagian_a=float(grand_total if is_last else 0),
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

    def fill_multipage(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> MultipagePlan:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk Stage 8C.9.") from exc

        l1_service = Legacy1770LampiranIService()
        l2_service = Legacy1770LampiranIIService()
        l4_service = Legacy1770LampiranIVService()
        l1 = l1_service.map_document(document)
        l2 = l2_service.map_document(document)
        l4 = l4_service.map_document(document)
        plan = self.build_plan(document)

        if not document.can_export_pdf or not l1.can_fill or not l2.can_fill or not l4.can_fill:
            plan.issues.append(
                MultipageIssue(
                    "MP_001",
                    "ERROR",
                    "Snapshot FINAL atau mapping lampiran belum siap untuk ekspor multipage.",
                )
            )
            return plan

        with TemporaryDirectory(prefix="tax1770_mp_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_8c8.pdf"
            base_result = l4_service.fill_lampiran_iv(
                document,
                base_pdf,
                template_path=template_path,
            )
            if not base_result.can_fill:
                plan.issues.append(
                    MultipageIssue("MP_002", "ERROR", "Output dasar Stage 8C.8 gagal dibentuk.")
                )
                return plan

            base_reader = PdfReader(str(base_pdf))
            if len(base_reader.pages) != 6:
                raise ValueError("Output dasar Stage 8C.8 harus tepat 6 halaman.")

            if template_path is None:
                from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH

                template_path = DEFAULT_TEMPLATE_PATH
            template_reader = PdfReader(str(template_path))
            if len(template_reader.pages) != 6:
                raise ValueError("Master 1770 Stage 8C.9 harus tepat 6 halaman.")

            # Footer page numbering dan masking total pada halaman dasar bila
            # kelompok tersebut memiliki halaman lanjutan.
            base_l1 = base_reader.pages[2]
            self._merge_stream(
                base_l1,
                self._make_footer_overlay(
                    base_l1,
                    1,
                    plan.lampiran_i_c_pages,
                    self.L1_PAGE_BOX,
                    self.L1_TOTAL_BOX,
                    clear_total_rect=(l1_service.C_TOTAL_RECT if plan.lampiran_i_c_pages > 1 else None),
                    draw_dash=plan.lampiran_i_c_pages > 1,
                ),
            )

            base_l2 = base_reader.pages[3]
            self._merge_stream(
                base_l2,
                self._make_footer_overlay(
                    base_l2,
                    1,
                    plan.lampiran_ii_pages,
                    self.L2_PAGE_BOX,
                    self.L2_TOTAL_BOX,
                    clear_total_rect=(l2_service.TOTAL_RECT if plan.lampiran_ii_pages > 1 else None),
                    draw_dash=plan.lampiran_ii_pages > 1,
                ),
            )

            base_l4 = base_reader.pages[5]
            self._merge_stream(
                base_l4,
                self._make_footer_overlay(
                    base_l4,
                    1,
                    plan.lampiran_iv_pages,
                    self.L4_PAGE_BOX,
                    self.L4_TOTAL_BOX,
                    clear_total_rect=(l4_service.HARTA_TOTAL_RECT if plan.lampiran_iv_pages > 1 else None),
                    draw_dash=plan.lampiran_iv_pages > 1,
                ),
            )

            writer = PdfWriter()
            writer.add_page(base_reader.pages[0])
            writer.add_page(base_reader.pages[1])
            writer.add_page(base_l1)

            # Lampiran I halaman tipe-3: 6 baris per halaman.
            l1_size = l1_service.MAX_EMPLOYMENT_ROWS
            for page_index in range(1, plan.lampiran_i_c_pages):
                start = page_index * l1_size
                rows = l1.employment_rows[start : start + l1_size]
                writer.add_page(
                    self._build_l1_continuation(
                        template_reader.pages[2],
                        document,
                        rows,
                        l1.jumlah_bagian_c,
                        page_index + 1,
                        plan.lampiran_i_c_pages,
                        is_last=page_index == plan.lampiran_i_c_pages - 1,
                    )
                )

            writer.add_page(base_l2)

            # Lampiran II: 15 Bupot per halaman.
            l2_size = l2_service.MAX_ROWS
            for page_index in range(1, plan.lampiran_ii_pages):
                start = page_index * l2_size
                rows = l2.rows[start : start + l2_size]
                writer.add_page(
                    self._build_l2_continuation(
                        template_reader.pages[3],
                        document,
                        rows,
                        l2.jumlah_bagian_a,
                        page_index + 1,
                        plan.lampiran_ii_pages,
                        is_last=page_index == plan.lampiran_ii_pages - 1,
                    )
                )

            writer.add_page(base_reader.pages[4])
            writer.add_page(base_l4)

            # Lampiran IV Harta: 10 baris per halaman.
            l4_size = l4_service.MAX_HARTA_ROWS
            for page_index in range(1, plan.lampiran_iv_pages):
                start = page_index * l4_size
                rows = l4.harta_rows[start : start + l4_size]
                writer.add_page(
                    self._build_l4_continuation(
                        template_reader.pages[5],
                        document,
                        rows,
                        l4.jumlah_bagian_a,
                        page_index + 1,
                        plan.lampiran_iv_pages,
                        is_last=page_index == plan.lampiran_iv_pages - 1,
                    )
                )

            for page in writer.pages:
                self._sanitize_page(page)
            root = writer._root_object
            for key in ("/AcroForm", "/OpenAction", "/AA"):
                if key in root:
                    del root[key]

            target = Path(output_path)
            if target.suffix.lower() != ".pdf":
                target = target.with_suffix(".pdf")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                writer.write(handle)

        return plan
