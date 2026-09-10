from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class LampiranIIBupotRow:
    nomor: int
    nama_pemotong: str
    npwp_pemotong: str
    no_bupot: str
    tanggal_bupot: str
    jenis_pajak: str
    pph_dipotong: float


@dataclass(frozen=True)
class LampiranIIIssue:
    code: str
    severity: str
    message: str


@dataclass
class LampiranIIMappingResult:
    rows: List[LampiranIIBupotRow] = field(default_factory=list)
    jumlah_bagian_a: float = 0.0
    detail_pph_total: float = 0.0
    issues: List[LampiranIIIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LampiranIIIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[LampiranIIIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def can_fill(self) -> bool:
        return not self.errors


class Legacy1770LampiranIIService:
    """Stage 8C.6 - cetak Lampiran II pada halaman 4 master bersih.

    Koordinat header sengaja berdiri sendiri. Header tiap halaman Form 1770 tidak
    diasumsikan identik karena posisi kotaknya memang memiliki selisih kecil.
    Seluruh data berasal dari Legacy1770Document snapshot FINAL WP aktif.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0
    PAGE_INDEX = 3
    MAX_ROWS = 15

    # Header khusus halaman 4 / Lampiran II, dikalibrasi dari master halaman ini.
    YEAR_CELL_CENTERS: Sequence[float] = (469.93, 502.57, 533.53, 563.67)
    YEAR_BASELINE_TOP = 38.90
    YEAR_FONT_SIZE = 15.384

    PERIOD_START_CELL_CENTERS: Sequence[float] = (462.36, 478.92, 494.88, 510.84)
    PERIOD_END_CELL_CENTERS: Sequence[float] = (541.58, 556.94, 572.06, 587.06)
    PERIOD_BASELINE_TOP = 67.22
    PERIOD_FONT_SIZE = 7.704

    NPWP_CELL_CENTERS: Sequence[float] = (
        157.48,
        173.44,
        189.40,
        205.36,
        237.31,
        253.99,
        270.55,
        286.51,
        317.23,
        332.01,
        347.97,
        363.93,
        395.85,
        411.81,
        428.76,
        445.68,
    )
    NPWP_BASELINE_TOP = 131.06
    NPWP_FONT_SIZE = 7.704

    NAME_X = 150.62
    NAME_BASELINE_TOP = 150.50
    NAME_FONT_SIZE = 7.704
    NAME_MAX_X = 563.50

    # Tabel Lampiran II Bagian A.
    ROW_START_TOP = 244.31
    ROW_HEIGHT = 33.96
    NAME_X_RANGE = (46.02, 148.64)
    NPWP_X_RANGE = (149.48, 244.43)
    BUPOT_X_RANGE = (245.27, 309.59)
    DATE_X_RANGE = (310.43, 371.05)
    TYPE_X_RANGE = (371.89, 470.08)
    PPH_X_RANGE = (470.92, 594.18)
    TOTAL_RECT: Rect = (470.92, 753.71, 594.18, 787.72)

    @staticmethod
    def _meaningful_bupot(row: Legacy1770BupotRow) -> bool:
        return bool(
            str(row.nama_pemotong or "").strip()
            or str(row.npwp_pemotong or "").strip()
            or str(row.no_bupot or "").strip()
            or str(row.tanggal_bupot or "").strip()
            or str(row.jenis or "").strip()
            or float(row.pph_dipotong or 0)
            or float(row.bruto or 0)
            or float(row.pengurang or 0)
        )

    @staticmethod
    def _jenis_pajak(value: object) -> str:
        raw = " ".join(str(value or "").strip().split())
        if not raw:
            return ""
        upper = raw.upper().replace("-", " ")
        if "DTP" in upper:
            return "DTP"
        for code in ("21", "22", "23", "24", "26"):
            if code in upper:
                return f"PPh Pasal {code}"
        return raw

    @staticmethod
    def _tanggal(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
        ):
            try:
                return datetime.strptime(text[:10], fmt).strftime("%d/%m/%Y")
            except ValueError:
                pass
        return text

    def map_document(self, document: Legacy1770Document) -> LampiranIIMappingResult:
        result = LampiranIIMappingResult()
        if not document.npwp:
            result.issues.append(LampiranIIIssue("L2_001", "ERROR", "NPWP FINAL tidak tersedia."))
        if not document.nama_wp:
            result.issues.append(LampiranIIIssue("L2_002", "ERROR", "Nama WP FINAL tidak tersedia."))
        if not document.tahun_pajak:
            result.issues.append(LampiranIIIssue("L2_003", "ERROR", "Tahun Pajak FINAL tidak tersedia."))
        if result.errors:
            return result

        for index, row in enumerate(
            (item for item in document.bupot_rows if self._meaningful_bupot(item)),
            start=1,
        ):
            result.rows.append(
                LampiranIIBupotRow(
                    nomor=index,
                    nama_pemotong=" ".join(str(row.nama_pemotong or "").strip().split()),
                    npwp_pemotong="".join(ch for ch in str(row.npwp_pemotong or "") if ch.isdigit()),
                    no_bupot=str(row.no_bupot or "").strip(),
                    tanggal_bupot=self._tanggal(row.tanggal_bupot),
                    jenis_pajak=self._jenis_pajak(row.jenis),
                    pph_dipotong=float(row.pph_dipotong or 0),
                )
            )

        result.detail_pph_total = sum(row.pph_dipotong for row in result.rows)
        # JBA harus konsisten dengan angka 15 Induk. Snapshot saat ini sudah
        # memiliki total kredit pajak walau detail PPh tiap Bupot belum selalu ada.
        result.jumlah_bagian_a = float(document.kredit_pajak or result.detail_pph_total or 0)

        if len(result.rows) > self.MAX_ROWS:
            result.issues.append(
                LampiranIIIssue(
                    "L2_W01",
                    "WARNING",
                    f"Lampiran II memiliki {len(result.rows)} baris; Stage 8C.6 menampilkan 15 baris pertama. Halaman lanjutan ditangani pada Stage 8C.9.",
                )
            )

        incomplete = [
            row
            for row in result.rows
            if not row.nama_pemotong
            or not row.npwp_pemotong
            or not row.no_bupot
            or not row.tanggal_bupot
            or not row.jenis_pajak
            or abs(row.pph_dipotong) < 0.000001
        ]
        if incomplete:
            result.issues.append(
                LampiranIIIssue(
                    "L2_W02",
                    "WARNING",
                    f"{len(incomplete)} baris Lampiran II belum memiliki seluruh detail Nama/NPWP/No Bupot/Tanggal/Jenis/PPh Dipotong; field yang tidak tersedia dibiarkan kosong tanpa menebak data.",
                )
            )

        if result.rows and abs(result.detail_pph_total) < 0.000001 and result.jumlah_bagian_a:
            result.issues.append(
                LampiranIIIssue(
                    "L2_W03",
                    "WARNING",
                    "PPh Dipotong per Bupot belum tersedia pada snapshot. JBA memakai total Kredit Pajak FINAL agar tetap sama dengan angka 15 Induk.",
                )
            )
        elif result.detail_pph_total and result.jumlah_bagian_a and abs(result.detail_pph_total - result.jumlah_bagian_a) > 1.0:
            result.issues.append(
                LampiranIIIssue(
                    "L2_W04",
                    "WARNING",
                    "Jumlah PPh Dipotong detail berbeda dengan Kredit Pajak FINAL; JBA mengikuti total Kredit Pajak FINAL agar konsisten dengan Induk.",
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
    def _draw_fit_center(
        cls,
        canvas,
        rect: Rect,
        text: str,
        width: float,
        height: float,
        *,
        size: float = 6.2,
        min_size: float = 4.2,
    ) -> None:
        text = str(text or "").strip()
        if not text:
            return
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        actual = float(size)
        max_width = (x1 - x0) - (4.0 * sx)
        while actual > min_size:
            canvas.setFont("Helvetica", actual * sy)
            if canvas.stringWidth(text, "Helvetica", actual * sy) <= max_width:
                break
            actual -= 0.2
        font_size = actual * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawCentredString((x0 + x1) / 2.0, baseline, text)

    @classmethod
    def _draw_right_money(cls, canvas, rect: Rect, value: float, width: float, height: float, *, size: float = 6.4) -> None:
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
    def _draw_header(cls, canvas, document: Legacy1770Document, width: float, height: float) -> None:
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT

        year = f"{int(document.tahun_pajak):04d}"[-4:]
        canvas.setFont("Helvetica-Bold", cls.YEAR_FONT_SIZE * sy)
        year_y = height - (cls.YEAR_BASELINE_TOP * sy)
        for center_top, digit in zip(cls.YEAR_CELL_CENTERS, year):
            canvas.drawCentredString(center_top * sx, year_y, digit)

        for centers, text in (
            (cls.PERIOD_START_CELL_CENTERS, f"01{int(document.tahun_pajak) % 100:02d}"),
            (cls.PERIOD_END_CELL_CENTERS, f"12{int(document.tahun_pajak) % 100:02d}"),
        ):
            canvas.setFont("Helvetica", cls.PERIOD_FONT_SIZE * sy)
            y = height - (cls.PERIOD_BASELINE_TOP * sy)
            for center_top, digit in zip(centers, text):
                canvas.drawCentredString(center_top * sx, y, digit)

        digits = [ch for ch in str(document.npwp or "") if ch.isdigit()][:16]
        canvas.setFont("Helvetica", cls.NPWP_FONT_SIZE * sy)
        npwp_y = height - (cls.NPWP_BASELINE_TOP * sy)
        for center_top, digit in zip(cls.NPWP_CELL_CENTERS, digits):
            canvas.drawCentredString(center_top * sx, npwp_y, digit)

        name = str(document.nama_wp or "").strip().upper()
        if name:
            size = cls.NAME_FONT_SIZE
            max_width = (cls.NAME_MAX_X - cls.NAME_X) * sx
            while size > 5.2:
                canvas.setFont("Helvetica", size * sy)
                if canvas.stringWidth(name, "Helvetica", size * sy) <= max_width:
                    break
                size -= 0.2
            canvas.setFont("Helvetica", size * sy)
            _, name_y = cls._pdf_xy(cls.NAME_X, cls.NAME_BASELINE_TOP, width, height)
            canvas.drawString(cls.NAME_X * sx, name_y, name)

    def _make_overlay(self, page, document: Legacy1770Document, mapping: LampiranIIMappingResult):
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Lampiran II.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_header(canvas, document, width, height)

        for index, row in enumerate(mapping.rows[: self.MAX_ROWS]):
            y0 = self.ROW_START_TOP + (index * self.ROW_HEIGHT)
            y1 = y0 + self.ROW_HEIGHT
            self._draw_fit_center(canvas, (self.NAME_X_RANGE[0], y0, self.NAME_X_RANGE[1], y1), row.nama_pemotong.upper(), width, height, size=5.7)
            self._draw_fit_center(canvas, (self.NPWP_X_RANGE[0], y0, self.NPWP_X_RANGE[1], y1), row.npwp_pemotong, width, height, size=5.8)
            self._draw_fit_center(canvas, (self.BUPOT_X_RANGE[0], y0, self.BUPOT_X_RANGE[1], y1), row.no_bupot, width, height, size=5.5)
            self._draw_fit_center(canvas, (self.DATE_X_RANGE[0], y0, self.DATE_X_RANGE[1], y1), row.tanggal_bupot, width, height, size=5.5)
            self._draw_fit_center(canvas, (self.TYPE_X_RANGE[0], y0, self.TYPE_X_RANGE[1], y1), row.jenis_pajak, width, height, size=5.8)
            self._draw_right_money(canvas, (self.PPH_X_RANGE[0], y0, self.PPH_X_RANGE[1], y1), row.pph_dipotong, width, height, size=6.2)

        if abs(mapping.jumlah_bagian_a) > 0.000001:
            # Master bersih memiliki tanda '-' statis pada kotak JBA.
            x0, y0, x1, y1 = self._pdf_rect(self.TOTAL_RECT, width, height)
            canvas.setFillColor(Color(1.0, 1.0, 0.60))
            canvas.rect(x0 + 0.8, y0 + 0.8, (x1 - x0) - 1.6, (y1 - y0) - 1.6, stroke=0, fill=1)
            canvas.setFillColorRGB(0, 0, 0)
            self._draw_right_money(canvas, self.TOTAL_RECT, mapping.jumlah_bagian_a, width, height, size=7.0)

        canvas.save()
        packet.seek(0)
        return packet

    def fill_lampiran_ii(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> LampiranIIMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk membuat Lampiran II.") from exc

        from core.legacy_1770_lampiran_i_finetuned import Legacy1770LampiranIService

        with TemporaryDirectory(prefix="tax1770_l2_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_lampiran_i.pdf"
            previous = Legacy1770LampiranIService()
            previous_result = previous.fill_lampiran_i(document, base_pdf, template_path=template_path)
            if not previous_result.can_fill:
                mapping.issues.append(LampiranIIIssue("L2_004", "ERROR", "Induk/Lampiran I gagal dibentuk sebelum Lampiran II."))
                return mapping

            reader = PdfReader(str(base_pdf))
            if len(reader.pages) != 6:
                raise ValueError("Master/output 1770 harus tepat 6 halaman.")

            overlay_page = PdfReader(self._make_overlay(reader.pages[self.PAGE_INDEX], document, mapping)).pages[0]
            reader.pages[self.PAGE_INDEX].merge_page(overlay_page)

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
