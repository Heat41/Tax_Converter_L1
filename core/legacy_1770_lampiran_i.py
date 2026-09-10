from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document, Legacy1770BupotRow


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class LampiranIEmploymentRow:
    nomor: int
    nama_pemberi_kerja: str
    npwp_pemberi_kerja: str
    bruto: float
    pengurang: float
    netto: float


@dataclass(frozen=True)
class LampiranIIssue:
    code: str
    severity: str
    message: str


@dataclass
class LampiranIMappingResult:
    employment_rows: List[LampiranIEmploymentRow] = field(default_factory=list)
    jumlah_bagian_c: float = 0.0
    jumlah_bagian_d: float = 0.0
    issues: List[LampiranIIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LampiranIIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[LampiranIIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def can_fill(self) -> bool:
        return not self.errors


class Legacy1770LampiranIService:
    """Stage 8C.5 - cetak Lampiran I halaman 1 dan 2 secara statis.

    Renderer tidak menyimpan angka WP tertentu. Koordinat mengikuti master bersih
    1770 enam halaman, sedangkan seluruh isi berasal dari Legacy1770Document
    milik snapshot FINAL yang sedang diekspor.

    Cakupan data domain saat ini:
    - Halaman 1 / Bagian A: identitas dan periode. Detail laporan keuangan belum
      dimodelkan sehingga tidak ditebak.
    - Halaman 2 / Bagian B: tidak diisi tanpa data norma/usaha yang lengkap.
    - Halaman 2 / Bagian C: berasal dari Bupot pekerjaan pada snapshot FINAL.
    - Halaman 2 / Bagian D: penghasilan neto dalam negeri lainnya ditempatkan
      pada baris "Penghasilan Lainnya" karena belum ada breakdown kategorinya.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0
    PAGE_1_INDEX = 1
    PAGE_2_INDEX = 2
    MAX_EMPLOYMENT_ROWS = 6

    # Header Lampiran I halaman 1/2. Koordinat origin kiri-atas pada master.
    YEAR_RECT: Rect = (450.0, 24.0, 575.0, 43.5)
    PERIOD_START_RECT: Rect = (450.0, 57.0, 513.5, 72.0)
    PERIOD_END_RECT: Rect = (529.0, 57.0, 590.5, 72.0)
    NPWP_GROUP_RECTS: Sequence[Rect] = (
        (149.0, 121.0, 212.0, 136.0),
        (228.5, 121.0, 291.0, 136.0),
        (307.5, 121.0, 370.5, 136.0),
        (386.5, 121.0, 450.0, 136.0),
    )
    NAME_RECT: Rect = (149.0, 140.5, 545.0, 155.5)

    # Lampiran I halaman 2 - Bagian C.
    C_NAME_X = (63.5, 212.0)
    C_BRUTO_X = (212.0, 338.5)
    C_PENGURANG_X = (338.5, 465.5)
    C_NETTO_X = (465.5, 590.5)
    C_ROW_Y: Sequence[Tuple[float, float]] = (
        (470.0, 490.5),
        (490.5, 510.5),
        (510.5, 531.0),
        (531.0, 551.0),
        (551.0, 571.5),
        (571.5, 591.5),
    )
    C_TOTAL_RECT: Rect = (465.5, 591.5, 590.5, 606.5)

    # Lampiran I halaman 2 - Bagian D.
    D_OTHER_RECT: Rect = (386.0, 786.0, 590.5, 808.0)
    D_TOTAL_RECT: Rect = (386.0, 808.0, 590.5, 830.5)

    @staticmethod
    def _meaningful_bupot(row: Legacy1770BupotRow) -> bool:
        return bool(
            str(row.npwp_pemotong or "").strip()
            or str(row.nama_pemotong or "").strip()
            or float(row.bruto or 0)
            or float(row.pengurang or 0)
            or float(row.netto or 0)
        )

    def map_document(self, document: Legacy1770Document) -> LampiranIMappingResult:
        result = LampiranIMappingResult()
        if not document.npwp:
            result.issues.append(LampiranIIssue("L1_001", "ERROR", "NPWP FINAL tidak tersedia."))
        if not document.nama_wp:
            result.issues.append(LampiranIIssue("L1_002", "ERROR", "Nama WP FINAL tidak tersedia."))
        if not document.tahun_pajak:
            result.issues.append(LampiranIIssue("L1_003", "ERROR", "Tahun Pajak FINAL tidak tersedia."))
        if result.errors:
            return result

        for index, row in enumerate(
            (item for item in document.bupot_rows if self._meaningful_bupot(item)),
            start=1,
        ):
            result.employment_rows.append(
                LampiranIEmploymentRow(
                    nomor=index,
                    nama_pemberi_kerja=str(row.nama_pemotong or "").strip(),
                    npwp_pemberi_kerja="".join(
                        ch for ch in str(row.npwp_pemotong or "") if ch.isdigit()
                    ),
                    bruto=float(row.bruto or 0),
                    pengurang=float(row.pengurang or 0),
                    netto=float(row.netto or 0),
                )
            )

        result.jumlah_bagian_c = sum(row.netto for row in result.employment_rows)
        result.jumlah_bagian_d = float(document.penghasilan_neto_lainnya or 0)

        expected_c = float(document.total_netto_bupot or 0)
        if abs(result.jumlah_bagian_c - expected_c) > 1.0:
            result.issues.append(
                LampiranIIssue(
                    "L1_W01",
                    "WARNING",
                    "Jumlah netto baris Bupot berbeda dengan total netto PPh pada snapshot FINAL; Lampiran I memakai jumlah baris Bupot aktual.",
                )
            )

        if len(result.employment_rows) > self.MAX_EMPLOYMENT_ROWS:
            result.issues.append(
                LampiranIIssue(
                    "L1_W02",
                    "WARNING",
                    f"Bagian C memiliki {len(result.employment_rows)} baris; Stage 8C.5 menampilkan 6 baris pertama. Duplikasi halaman lanjutan ditangani pada Stage 8C.9.",
                )
            )

        if any(row.npwp_pemberi_kerja and not row.nama_pemberi_kerja for row in result.employment_rows):
            result.issues.append(
                LampiranIIssue(
                    "L1_W03",
                    "WARNING",
                    "Nama pemberi kerja belum tersimpan pada sebagian Bupot; Lampiran I menampilkan NPWP yang tersedia tanpa menebak nama.",
                )
            )

        return result

    @classmethod
    def _pdf_xy(cls, x_top: float, y_top: float, width: float, height: float) -> Tuple[float, float]:
        return x_top * (width / cls.BASE_WIDTH), height - (y_top * (height / cls.BASE_HEIGHT))

    @classmethod
    def _pdf_rect(cls, rect: Rect, width: float, height: float) -> Rect:
        x0, y0, x1, y1 = rect
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        return x0 * sx, height - y1 * sy, x1 * sx, height - y0 * sy

    @classmethod
    def _draw_center(cls, canvas, rect: Rect, text: str, width: float, height: float, *, size: float = 6.6, bold: bool = False) -> None:
        if not text:
            return
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        font_size = size * sy
        canvas.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawCentredString((x0 + x1) / 2.0, baseline, text)

    @classmethod
    def _draw_left(cls, canvas, rect: Rect, text: str, width: float, height: float, *, size: float = 6.4) -> None:
        if not text:
            return
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        font_size = size * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawString(x0 + 2.0, baseline, text)

    @classmethod
    def _draw_right(cls, canvas, rect: Rect, value: float, width: float, height: float, *, size: float = 7.0) -> None:
        number = int(round(float(value or 0)))
        if number == 0:
            return
        text = ("-" if number < 0 else "") + f"{abs(number):,}".replace(",", ".")
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        font_size = size * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawRightString(x1 - 3.0, baseline, text)

    @classmethod
    def _draw_four_group_comb(cls, canvas, groups: Sequence[Rect], text: str, width: float, height: float) -> None:
        chars = [ch for ch in str(text or "") if ch.isdigit()]
        index = 0
        sy = height / cls.BASE_HEIGHT
        canvas.setFont("Helvetica", 7.0 * sy)
        for rect in groups:
            x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
            cell_width = (x1 - x0) / 4.0
            baseline = y0 + ((y1 - y0 - 7.0 * sy) / 2.0) + (1.6 * sy)
            for cell in range(4):
                if index >= len(chars):
                    return
                canvas.drawCentredString(x0 + cell_width * (cell + 0.5), baseline, chars[index])
                index += 1

    @classmethod
    def _draw_year(cls, canvas, year: int, width: float, height: float) -> None:
        digits = f"{int(year):04d}"[-4:]
        x0, y0, x1, y1 = cls._pdf_rect(cls.YEAR_RECT, width, height)
        cell_width = (x1 - x0) / 4.0
        sy = height / cls.BASE_HEIGHT
        canvas.setFont("Helvetica-Bold", 8.5 * sy)
        baseline = y0 + ((y1 - y0 - 8.5 * sy) / 2.0) + (1.5 * sy)
        for index, digit in enumerate(digits):
            canvas.drawCentredString(x0 + cell_width * (index + 0.5), baseline, digit)

    @classmethod
    def _draw_period(cls, canvas, rect: Rect, month: int, year: int, width: float, height: float) -> None:
        text = f"{int(month):02d}{int(year) % 100:02d}"
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        cell_width = (x1 - x0) / 4.0
        sy = height / cls.BASE_HEIGHT
        canvas.setFont("Helvetica", 6.0 * sy)
        baseline = y0 + ((y1 - y0 - 6.0 * sy) / 2.0) + (1.5 * sy)
        for index, digit in enumerate(text):
            canvas.drawCentredString(x0 + cell_width * (index + 0.5), baseline, digit)

    def _draw_header(self, canvas, document: Legacy1770Document, width: float, height: float) -> None:
        self._draw_year(canvas, document.tahun_pajak, width, height)
        self._draw_period(canvas, self.PERIOD_START_RECT, 1, document.tahun_pajak, width, height)
        self._draw_period(canvas, self.PERIOD_END_RECT, 12, document.tahun_pajak, width, height)
        self._draw_four_group_comb(canvas, self.NPWP_GROUP_RECTS, document.npwp, width, height)
        self._draw_left(canvas, self.NAME_RECT, str(document.nama_wp).upper(), width, height, size=7.0)

    def _make_page1_overlay(self, page, document: Legacy1770Document):
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Lampiran I.") from exc
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_header(canvas, document, width, height)
        canvas.save()
        packet.seek(0)
        return packet

    def _make_page2_overlay(self, page, document: Legacy1770Document, mapping: LampiranIMappingResult):
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Lampiran I.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_header(canvas, document, width, height)

        for row_index, row in enumerate(mapping.employment_rows[: self.MAX_EMPLOYMENT_ROWS]):
            y0, y1 = self.C_ROW_Y[row_index]
            name_rect = (self.C_NAME_X[0], y0, self.C_NAME_X[1], y1)
            bruto_rect = (self.C_BRUTO_X[0], y0, self.C_BRUTO_X[1], y1)
            pengurang_rect = (self.C_PENGURANG_X[0], y0, self.C_PENGURANG_X[1], y1)
            netto_rect = (self.C_NETTO_X[0], y0, self.C_NETTO_X[1], y1)

            if row.nama_pemberi_kerja and row.npwp_pemberi_kerja:
                mid = (y0 + y1) / 2.0
                self._draw_center(canvas, (name_rect[0], y0, name_rect[2], mid + 1.0), row.nama_pemberi_kerja.upper(), width, height, size=5.0)
                self._draw_center(canvas, (name_rect[0], mid - 1.0, name_rect[2], y1), row.npwp_pemberi_kerja, width, height, size=5.0)
            else:
                label = row.nama_pemberi_kerja.upper() or row.npwp_pemberi_kerja
                self._draw_center(canvas, name_rect, label, width, height, size=5.2)

            self._draw_right(canvas, bruto_rect, row.bruto, width, height, size=6.5)
            self._draw_right(canvas, pengurang_rect, row.pengurang, width, height, size=6.5)
            self._draw_right(canvas, netto_rect, row.netto, width, height, size=6.5)

        self._draw_right(canvas, self.C_TOTAL_RECT, mapping.jumlah_bagian_c, width, height, size=7.2)

        if abs(mapping.jumlah_bagian_d) > 0.000001:
            # Master bersih masih memiliki tanda '-' statis pada sel total Bagian D.
            # Tutup bagian dalam sel dengan warna kuning form, pertahankan border.
            yellow = Color(1.0, 1.0, 0.60)
            for rect in (self.D_OTHER_RECT, self.D_TOTAL_RECT):
                x0, y0, x1, y1 = self._pdf_rect(rect, width, height)
                canvas.setFillColor(yellow)
                canvas.rect(x0 + 0.8, y0 + 0.8, (x1 - x0) - 1.6, (y1 - y0) - 1.6, stroke=0, fill=1)
                canvas.setFillColorRGB(0, 0, 0)
            self._draw_right(canvas, self.D_OTHER_RECT, mapping.jumlah_bagian_d, width, height, size=7.0)
            self._draw_right(canvas, self.D_TOTAL_RECT, mapping.jumlah_bagian_d, width, height, size=7.2)

        canvas.save()
        packet.seek(0)
        return packet

    def fill_lampiran_i(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> LampiranIMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk membuat Lampiran I.") from exc

        # Gunakan renderer Induk yang sudah dikunci agar output uji Stage 8C.5
        # tetap memuat halaman 1 yang benar, lalu tambahkan Lampiran I halaman 1/2.
        from core.legacy_1770_induk_finetuned import Legacy1770IndukService

        with TemporaryDirectory(prefix="tax1770_l1_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_induk.pdf"
            induk = Legacy1770IndukService()
            induk_result = induk.fill_induk(document, base_pdf, template_path=template_path)
            if not induk_result.can_fill:
                mapping.issues.append(LampiranIIssue("L1_004", "ERROR", "Form Induk gagal dibentuk sebelum Lampiran I."))
                return mapping

            reader = PdfReader(str(base_pdf))
            if len(reader.pages) != 6:
                raise ValueError("Master/output 1770 harus tepat 6 halaman.")

            for page_index, overlay_stream in (
                (self.PAGE_1_INDEX, self._make_page1_overlay(reader.pages[self.PAGE_1_INDEX], document)),
                (self.PAGE_2_INDEX, self._make_page2_overlay(reader.pages[self.PAGE_2_INDEX], document, mapping)),
            ):
                overlay_page = PdfReader(overlay_stream).pages[0]
                reader.pages[page_index].merge_page(overlay_page)

            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            target = Path(output_path)
            if target.suffix.lower() != ".pdf":
                target = target.with_suffix(".pdf")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                writer.write(handle)

        return mapping
