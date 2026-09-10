from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document


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

    Koordinat mengikuti master bersih 1770 enam halaman. Seluruh nilai berasal
    dari Legacy1770Document milik snapshot FINAL WP yang sedang diekspor; tidak
    ada nilai WP contoh yang ditanam di renderer.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0
    PAGE_1_INDEX = 1
    PAGE_2_INDEX = 2
    MAX_EMPLOYMENT_ROWS = 6

    # ------------------------------------------------------------------
    # Header Lampiran I halaman 1 dan 2.
    # Kalibrasi diambil dari posisi teks asli pada master 1770 enam halaman.
    # Koordinat X adalah pusat tiap kotak; Y adalah baseline dengan origin
    # kiri-atas agar hasil overlay mengikuti posisi tulisan contoh master.
    # ------------------------------------------------------------------
    YEAR_CELL_CENTERS: Sequence[float] = (465.88, 497.56, 529.25, 559.98)
    YEAR_BASELINE_TOP = 38.90
    YEAR_FONT_SIZE = 15.384

    PERIOD_START_CELL_CENTERS: Sequence[float] = (457.96, 473.80, 489.64, 505.48)
    PERIOD_END_CELL_CENTERS: Sequence[float] = (537.17, 553.02, 567.90, 582.78)
    PERIOD_BASELINE_TOP = 67.22
    PERIOD_FONT_SIZE = 7.704

    NPWP_CELL_CENTERS: Sequence[float] = (
        157.32,
        173.16,
        189.00,
        204.84,
        236.55,
        252.39,
        268.23,
        284.07,
        315.80,
        331.64,
        347.48,
        363.32,
        394.97,
        410.81,
        426.61,
        442.52,
    )
    NPWP_BASELINE_TOP = 131.06
    NPWP_FONT_SIZE = 7.704

    NAME_X = 150.50
    NAME_BASELINE_TOP = 150.50
    NAME_FONT_SIZE = 7.704
    NAME_MAX_X = 544.50

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
    C_IDENTITY_NAME_BASELINE_OFFSET = 7.0
    C_IDENTITY_NPWP_BASELINE_OFFSET = 17.0
    C_IDENTITY_FONT_SIZE = 5.2
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
            result.issues.append(
                LampiranIIssue("L1_001", "ERROR", "NPWP FINAL tidak tersedia.")
            )
        if not document.nama_wp:
            result.issues.append(
                LampiranIIssue("L1_002", "ERROR", "Nama WP FINAL tidak tersedia.")
            )
        if not document.tahun_pajak:
            result.issues.append(
                LampiranIIssue("L1_003", "ERROR", "Tahun Pajak FINAL tidak tersedia.")
            )
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

        if any(
            row.npwp_pemberi_kerja and not row.nama_pemberi_kerja
            for row in result.employment_rows
        ):
            result.issues.append(
                LampiranIIssue(
                    "L1_W03",
                    "WARNING",
                    "Nama pemberi kerja belum tersimpan pada sebagian Bupot; Lampiran I menampilkan NPWP yang tersedia tanpa menebak nama.",
                )
            )

        return result

    @classmethod
    def _pdf_xy(
        cls,
        x_top: float,
        y_top: float,
        width: float,
        height: float,
    ) -> Tuple[float, float]:
        return (
            x_top * (width / cls.BASE_WIDTH),
            height - (y_top * (height / cls.BASE_HEIGHT)),
        )

    @classmethod
    def _pdf_rect(cls, rect: Rect, width: float, height: float) -> Rect:
        x0, y0, x1, y1 = rect
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        return x0 * sx, height - y1 * sy, x1 * sx, height - y0 * sy

    @classmethod
    def _draw_center(
        cls,
        canvas,
        rect: Rect,
        text: str,
        width: float,
        height: float,
        *,
        size: float = 6.6,
        bold: bool = False,
    ) -> None:
        if not text:
            return
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        font_size = size * sy
        canvas.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawCentredString((x0 + x1) / 2.0, baseline, text)

    @classmethod
    def _draw_right(
        cls,
        canvas,
        rect: Rect,
        value: float,
        width: float,
        height: float,
        *,
        size: float = 7.0,
    ) -> None:
        number = int(round(float(value or 0)))
        if number == 0:
            return
        text = ("-" if number < 0 else "") + f"{abs(number):,}".replace(",", ".")
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sy = height / cls.BASE_HEIGHT
        font_size = size * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawRightString(x1 - (3.0 * width / cls.BASE_WIDTH), baseline, text)

    @classmethod
    def _draw_center_at_top_baseline(
        cls,
        canvas,
        x_top: float,
        baseline_top: float,
        text: str,
        width: float,
        height: float,
        *,
        size: float,
        bold: bool = False,
        max_width_top: Optional[float] = None,
        min_size: float = 4.2,
    ) -> None:
        """Gambar teks berdasarkan baseline master dan shrink bila terlalu panjang."""
        if not text:
            return
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        actual_size = float(size)
        if max_width_top is not None:
            while actual_size > min_size:
                canvas.setFont(font_name, actual_size * sy)
                if canvas.stringWidth(text, font_name, actual_size * sy) <= max_width_top * sx:
                    break
                actual_size -= 0.2
        canvas.setFont(font_name, actual_size * sy)
        x, y = cls._pdf_xy(x_top, baseline_top, width, height)
        canvas.drawCentredString(x, y, text)

    @classmethod
    def _draw_header(cls, canvas, document: Legacy1770Document, width: float, height: float) -> None:
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT

        # Tahun Pajak: ukuran dan baseline mengikuti master asli.
        year = f"{int(document.tahun_pajak):04d}"[-4:]
        canvas.setFont("Helvetica-Bold", cls.YEAR_FONT_SIZE * sy)
        year_y = height - (cls.YEAR_BASELINE_TOP * sy)
        for center_top, digit in zip(cls.YEAR_CELL_CENTERS, year):
            canvas.drawCentredString(center_top * sx, year_y, digit)

        # Masa Pajak: 01YY s.d. 12YY.
        for centers, text in (
            (cls.PERIOD_START_CELL_CENTERS, f"01{int(document.tahun_pajak) % 100:02d}"),
            (cls.PERIOD_END_CELL_CENTERS, f"12{int(document.tahun_pajak) % 100:02d}"),
        ):
            canvas.setFont("Helvetica", cls.PERIOD_FONT_SIZE * sy)
            period_y = height - (cls.PERIOD_BASELINE_TOP * sy)
            for center_top, digit in zip(centers, text):
                canvas.drawCentredString(center_top * sx, period_y, digit)

        # NPWP 16 digit: satu digit per kotak persis seperti master.
        npwp_digits = [ch for ch in str(document.npwp or "") if ch.isdigit()][:16]
        canvas.setFont("Helvetica", cls.NPWP_FONT_SIZE * sy)
        npwp_y = height - (cls.NPWP_BASELINE_TOP * sy)
        for center_top, digit in zip(cls.NPWP_CELL_CENTERS, npwp_digits):
            canvas.drawCentredString(center_top * sx, npwp_y, digit)

        # Nama WP menggunakan baseline master; font otomatis mengecil hanya jika
        # nama sangat panjang, supaya tidak keluar dari kotak kuning.
        name = str(document.nama_wp or "").strip().upper()
        if name:
            font_name = "Helvetica"
            size = cls.NAME_FONT_SIZE
            max_width = (cls.NAME_MAX_X - cls.NAME_X) * sx
            while size > 5.2:
                canvas.setFont(font_name, size * sy)
                if canvas.stringWidth(name, font_name, size * sy) <= max_width:
                    break
                size -= 0.2
            canvas.setFont(font_name, size * sy)
            _, name_y = cls._pdf_xy(cls.NAME_X, cls.NAME_BASELINE_TOP, width, height)
            canvas.drawString(cls.NAME_X * sx, name_y, name)

    @classmethod
    def _draw_employment_identity(
        cls,
        canvas,
        row: LampiranIEmploymentRow,
        y0: float,
        y1: float,
        width: float,
        height: float,
    ) -> None:
        """Cetak Nama di sub-baris atas dan NPWP di sub-baris bawah.

        Pada master, kolom Nama/NPWP memiliki garis pemisah horizontal di tengah
        setiap baris. NPWP tidak boleh lagi dicetak di tengah baris penuh karena
        akan tepat menimpa garis tersebut ketika nama pemberi kerja belum ada.
        """
        center_x = (cls.C_NAME_X[0] + cls.C_NAME_X[1]) / 2.0
        max_width = (cls.C_NAME_X[1] - cls.C_NAME_X[0]) - 5.0

        if row.nama_pemberi_kerja:
            cls._draw_center_at_top_baseline(
                canvas,
                center_x,
                y0 + cls.C_IDENTITY_NAME_BASELINE_OFFSET,
                row.nama_pemberi_kerja.upper(),
                width,
                height,
                size=cls.C_IDENTITY_FONT_SIZE,
                max_width_top=max_width,
            )

        if row.npwp_pemberi_kerja:
            cls._draw_center_at_top_baseline(
                canvas,
                center_x,
                min(y0 + cls.C_IDENTITY_NPWP_BASELINE_OFFSET, y1 - 2.2),
                row.npwp_pemberi_kerja,
                width,
                height,
                size=cls.C_IDENTITY_FONT_SIZE,
                max_width_top=max_width,
            )

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

    def _make_page2_overlay(
        self,
        page,
        document: Legacy1770Document,
        mapping: LampiranIMappingResult,
    ):
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

        for row_index, row in enumerate(
            mapping.employment_rows[: self.MAX_EMPLOYMENT_ROWS]
        ):
            y0, y1 = self.C_ROW_Y[row_index]
            bruto_rect = (self.C_BRUTO_X[0], y0, self.C_BRUTO_X[1], y1)
            pengurang_rect = (self.C_PENGURANG_X[0], y0, self.C_PENGURANG_X[1], y1)
            netto_rect = (self.C_NETTO_X[0], y0, self.C_NETTO_X[1], y1)

            self._draw_employment_identity(canvas, row, y0, y1, width, height)
            self._draw_right(canvas, bruto_rect, row.bruto, width, height, size=6.5)
            self._draw_right(
                canvas, pengurang_rect, row.pengurang, width, height, size=6.5
            )
            self._draw_right(canvas, netto_rect, row.netto, width, height, size=6.5)

        self._draw_right(
            canvas,
            self.C_TOTAL_RECT,
            mapping.jumlah_bagian_c,
            width,
            height,
            size=7.2,
        )

        if abs(mapping.jumlah_bagian_d) > 0.000001:
            # Master bersih memiliki tanda '-' statis pada sel Bagian D.
            # Tutup hanya isi sel kuning lalu cetak nilai dinamisnya.
            yellow = Color(1.0, 1.0, 0.60)
            for rect in (self.D_OTHER_RECT, self.D_TOTAL_RECT):
                x0, y0, x1, y1 = self._pdf_rect(rect, width, height)
                canvas.setFillColor(yellow)
                canvas.rect(
                    x0 + 0.8,
                    y0 + 0.8,
                    (x1 - x0) - 1.6,
                    (y1 - y0) - 1.6,
                    stroke=0,
                    fill=1,
                )
                canvas.setFillColorRGB(0, 0, 0)
            self._draw_right(
                canvas,
                self.D_OTHER_RECT,
                mapping.jumlah_bagian_d,
                width,
                height,
                size=7.0,
            )
            self._draw_right(
                canvas,
                self.D_TOTAL_RECT,
                mapping.jumlah_bagian_d,
                width,
                height,
                size=7.2,
            )

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

        # Gunakan renderer Induk yang sudah dikunci agar output Stage 8C.5 tetap
        # memuat halaman Induk final, lalu overlay Lampiran I halaman 1 dan 2.
        from core.legacy_1770_induk_finetuned import Legacy1770IndukService

        with TemporaryDirectory(prefix="tax1770_l1_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_induk.pdf"
            induk = Legacy1770IndukService()
            induk_result = induk.fill_induk(
                document,
                base_pdf,
                template_path=template_path,
            )
            if not induk_result.can_fill:
                mapping.issues.append(
                    LampiranIIssue(
                        "L1_004",
                        "ERROR",
                        "Form Induk gagal dibentuk sebelum Lampiran I.",
                    )
                )
                return mapping

            reader = PdfReader(str(base_pdf))
            if len(reader.pages) != 6:
                raise ValueError("Master/output 1770 harus tepat 6 halaman.")

            for page_index, overlay_stream in (
                (
                    self.PAGE_1_INDEX,
                    self._make_page1_overlay(
                        reader.pages[self.PAGE_1_INDEX], document
                    ),
                ),
                (
                    self.PAGE_2_INDEX,
                    self._make_page2_overlay(
                        reader.pages[self.PAGE_2_INDEX], document, mapping
                    ),
                ),
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
