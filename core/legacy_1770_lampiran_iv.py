from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document
from core.legacy_mapping import LegacyHartaRow


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class LampiranIVHartaRow:
    nomor: int
    kode_harta: str
    nama_harta: str
    tahun_perolehan: int
    harga_perolehan: float
    keterangan: str


@dataclass(frozen=True)
class LampiranIVIssue:
    code: str
    severity: str
    message: str


@dataclass
class LampiranIVMappingResult:
    harta_rows: List[LampiranIVHartaRow] = field(default_factory=list)
    jumlah_bagian_a: float = 0.0
    utang_rows_count: int = 0
    jumlah_bagian_b: float = 0.0
    anggota_keluarga_count: int = 0
    issues: List[LampiranIVIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LampiranIVIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[LampiranIVIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def can_fill(self) -> bool:
        return not self.errors


class Legacy1770LampiranIVService:
    """Stage 8C.8 - cetak Lampiran IV pada halaman 6 master bersih.

    Header halaman 6 dikalibrasi mandiri, tidak memakai koordinat Lampiran III.
    Bagian A berasal dari mapping Harta snapshot FINAL. Bagian B (Utang) dan
    Bagian C (Susunan Anggota Keluarga) tetap kosong sampai domain tersebut
    tersedia; renderer tidak menebak data yang tidak ada.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0
    PAGE_INDEX = 5
    MAX_HARTA_ROWS = 10

    # ------------------------------------------------------------------
    # Header khusus halaman 6 / Lampiran IV.
    # Nilai X diambil dari pusat glyph contoh pada master halaman 6; baseline
    # dikalibrasi terpisah karena posisi header berbeda dari halaman 5.
    # ------------------------------------------------------------------
    YEAR_CELL_CENTERS: Sequence[float] = (
        459.3834,
        490.5834,
        521.7834,
        552.1634,
    )
    YEAR_BASELINE_TOP = 42.04
    YEAR_FONT_SIZE = 15.384

    PERIOD_START_CELL_CENTERS: Sequence[float] = (
        451.9683,
        467.5683,
        483.1684,
        498.7684,
    )
    PERIOD_END_CELL_CENTERS: Sequence[float] = (
        529.9683,
        545.5883,
        560.3483,
        573.5483,
    )
    PERIOD_BASELINE_TOP = 64.41
    PERIOD_FONT_SIZE = 7.704

    NPWP_CELL_CENTERS: Sequence[float] = (
        171.0883,
        186.6884,
        202.2883,
        217.9184,
        249.1183,
        264.7183,
        280.3183,
        295.9184,
        327.1384,
        342.7384,
        358.3384,
        373.9383,
        405.1384,
        420.7384,
        436.3684,
        451.9683,
    )
    NPWP_BASELINE_TOP = 121.60
    NPWP_FONT_SIZE = 7.704

    NAME_X = 164.42
    NAME_BASELINE_TOP = 139.14
    NAME_FONT_SIZE = 7.704
    NAME_MAX_X = 570.0

    # ------------------------------------------------------------------
    # Bagian A - Harta pada akhir tahun.
    # Master mempunyai 10 baris fisik; halaman tambahan ditangani Stage 8C.9.
    # ------------------------------------------------------------------
    HARTA_ROW_BOUNDS: Sequence[Tuple[float, float]] = (
        (203.69, 220.25),
        (220.25, 236.45),
        (236.45, 252.65),
        (252.65, 268.85),
        (268.85, 285.05),
        (285.05, 301.25),
        (301.25, 317.45),
        (317.45, 333.65),
        (333.65, 349.85),
        (349.85, 365.69),
    )
    HARTA_CODE_X = (63.00, 100.68)
    HARTA_NAME_X = (101.40, 224.93)
    HARTA_YEAR_X = (225.65, 318.53)
    HARTA_VALUE_X = (319.27, 458.97)
    HARTA_NOTE_X = (459.70, 580.80)
    HARTA_TOTAL_RECT: Rect = (318.91, 366.05, 459.45, 382.39)

    @staticmethod
    def _meaningful_harta(row: LegacyHartaRow) -> bool:
        return bool(
            str(row.kode_eform or "").strip()
            or str(row.nama_harta or "").strip()
            or int(row.tahun_perolehan or 0)
            or float(row.nilai_tahun_berjalan or 0)
            or str(row.keterangan or "").strip()
        )

    def map_document(self, document: Legacy1770Document) -> LampiranIVMappingResult:
        result = LampiranIVMappingResult()
        if not document.npwp:
            result.issues.append(
                LampiranIVIssue("L4_001", "ERROR", "NPWP FINAL tidak tersedia.")
            )
        if not document.nama_wp:
            result.issues.append(
                LampiranIVIssue("L4_002", "ERROR", "Nama WP FINAL tidak tersedia.")
            )
        if not document.tahun_pajak:
            result.issues.append(
                LampiranIVIssue("L4_003", "ERROR", "Tahun Pajak FINAL tidak tersedia.")
            )
        if result.errors:
            return result

        meaningful_rows = [row for row in document.harta_rows if self._meaningful_harta(row)]
        for index, row in enumerate(meaningful_rows, start=1):
            result.harta_rows.append(
                LampiranIVHartaRow(
                    nomor=index,
                    kode_harta=str(row.kode_eform or "").strip(),
                    nama_harta=" ".join(str(row.nama_harta or "").strip().split()),
                    tahun_perolehan=int(row.tahun_perolehan or 0),
                    # Legacy mapping Harta memakai nilai tahun berjalan sebagai
                    # nilai Harta yang dibawa ke output Format Lama.
                    harga_perolehan=float(row.nilai_tahun_berjalan or 0),
                    keterangan=" ".join(str(row.keterangan or "").strip().split()),
                )
            )

        result.jumlah_bagian_a = sum(row.harga_perolehan for row in result.harta_rows)

        if not result.harta_rows:
            result.issues.append(
                LampiranIVIssue(
                    "L4_W01",
                    "WARNING",
                    "Snapshot FINAL tidak memiliki baris Harta yang dapat dicetak pada Lampiran IV.",
                )
            )

        if len(result.harta_rows) > self.MAX_HARTA_ROWS:
            result.issues.append(
                LampiranIVIssue(
                    "L4_W02",
                    "WARNING",
                    f"Lampiran IV memiliki {len(result.harta_rows)} baris Harta; Stage 8C.8 menampilkan 10 baris pertama. Halaman lanjutan ditangani pada Stage 8C.9.",
                )
            )

        # Domain Worksheet saat ini belum mempunyai daftar Utang dan anggota
        # keluarga yang lengkap. Tetap kosong, tanpa asumsi data.
        result.issues.append(
            LampiranIVIssue(
                "L4_W03",
                "WARNING",
                "Bagian B Utang dan Bagian C Susunan Anggota Keluarga belum mempunyai sumber data lengkap; keduanya dibiarkan kosong.",
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
        return x_top * (width / cls.BASE_WIDTH), height - (y_top * (height / cls.BASE_HEIGHT))

    @classmethod
    def _pdf_rect(cls, rect: Rect, width: float, height: float) -> Rect:
        x0, y0, x1, y1 = rect
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        return x0 * sx, height - y1 * sy, x1 * sx, height - y0 * sy

    @classmethod
    def _fit_text(
        cls,
        canvas,
        text: str,
        max_width: float,
        *,
        start_size: float,
        min_size: float,
        scale_y: float,
    ) -> Tuple[str, float]:
        value = str(text or "").strip()
        if not value:
            return "", start_size

        size = float(start_size)
        while size > min_size:
            canvas.setFont("Helvetica", size * scale_y)
            if canvas.stringWidth(value, "Helvetica", size * scale_y) <= max_width:
                return value, size
            size -= 0.2

        canvas.setFont("Helvetica", min_size * scale_y)
        if canvas.stringWidth(value, "Helvetica", min_size * scale_y) <= max_width:
            return value, min_size

        suffix = "..."
        while value:
            candidate = value.rstrip() + suffix
            if canvas.stringWidth(candidate, "Helvetica", min_size * scale_y) <= max_width:
                return candidate, min_size
            value = value[:-1]
        return suffix, min_size

    @classmethod
    def _draw_fit_center(
        cls,
        canvas,
        rect: Rect,
        text: str,
        width: float,
        height: float,
        *,
        size: float = 5.9,
        min_size: float = 4.0,
    ) -> None:
        value = str(text or "").strip()
        if not value:
            return
        x0, y0, x1, y1 = cls._pdf_rect(rect, width, height)
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        value, actual = cls._fit_text(
            canvas,
            value,
            (x1 - x0) - (4.0 * sx),
            start_size=size,
            min_size=min_size,
            scale_y=sy,
        )
        font_size = actual * sy
        canvas.setFont("Helvetica", font_size)
        baseline = y0 + ((y1 - y0 - font_size) / 2.0) + (1.6 * sy)
        canvas.drawCentredString((x0 + x1) / 2.0, baseline, value)

    @classmethod
    def _draw_right_money(
        cls,
        canvas,
        rect: Rect,
        value: float,
        width: float,
        height: float,
        *,
        size: float = 6.0,
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
    def _draw_header(
        cls,
        canvas,
        document: Legacy1770Document,
        width: float,
        height: float,
    ) -> None:
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT

        year = f"{int(document.tahun_pajak):04d}"[-4:]
        canvas.setFont("Helvetica-Bold", cls.YEAR_FONT_SIZE * sy)
        year_y = height - (cls.YEAR_BASELINE_TOP * sy)
        for center, digit in zip(cls.YEAR_CELL_CENTERS, year):
            canvas.drawCentredString(center * sx, year_y, digit)

        canvas.setFont("Helvetica", cls.PERIOD_FONT_SIZE * sy)
        period_y = height - (cls.PERIOD_BASELINE_TOP * sy)
        for centers, text in (
            (cls.PERIOD_START_CELL_CENTERS, f"01{int(document.tahun_pajak) % 100:02d}"),
            (cls.PERIOD_END_CELL_CENTERS, f"12{int(document.tahun_pajak) % 100:02d}"),
        ):
            for center, digit in zip(centers, text):
                canvas.drawCentredString(center * sx, period_y, digit)

        digits = [ch for ch in str(document.npwp or "") if ch.isdigit()][:16]
        canvas.setFont("Helvetica", cls.NPWP_FONT_SIZE * sy)
        npwp_y = height - (cls.NPWP_BASELINE_TOP * sy)
        for center, digit in zip(cls.NPWP_CELL_CENTERS, digits):
            canvas.drawCentredString(center * sx, npwp_y, digit)

        name = str(document.nama_wp or "").strip().upper()
        if name:
            max_width = (cls.NAME_MAX_X - cls.NAME_X) * sx
            value, size = cls._fit_text(
                canvas,
                name,
                max_width,
                start_size=cls.NAME_FONT_SIZE,
                min_size=5.2,
                scale_y=sy,
            )
            canvas.setFont("Helvetica", size * sy)
            _, name_y = cls._pdf_xy(cls.NAME_X, cls.NAME_BASELINE_TOP, width, height)
            canvas.drawString(cls.NAME_X * sx, name_y, value)

    def _make_overlay(
        self,
        page,
        document: Legacy1770Document,
        mapping: LampiranIVMappingResult,
    ):
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Lampiran IV.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_header(canvas, document, width, height)

        for index, row in enumerate(mapping.harta_rows[: self.MAX_HARTA_ROWS]):
            y0, y1 = self.HARTA_ROW_BOUNDS[index]
            self._draw_fit_center(
                canvas,
                (self.HARTA_CODE_X[0], y0, self.HARTA_CODE_X[1], y1),
                row.kode_harta,
                width,
                height,
                size=5.7,
            )
            self._draw_fit_center(
                canvas,
                (self.HARTA_NAME_X[0], y0, self.HARTA_NAME_X[1], y1),
                row.nama_harta.upper(),
                width,
                height,
                size=5.5,
            )
            if row.tahun_perolehan:
                self._draw_fit_center(
                    canvas,
                    (self.HARTA_YEAR_X[0], y0, self.HARTA_YEAR_X[1], y1),
                    str(row.tahun_perolehan),
                    width,
                    height,
                    size=5.8,
                )
            self._draw_right_money(
                canvas,
                (self.HARTA_VALUE_X[0], y0, self.HARTA_VALUE_X[1], y1),
                row.harga_perolehan,
                width,
                height,
                size=5.9,
            )
            self._draw_fit_center(
                canvas,
                (self.HARTA_NOTE_X[0], y0, self.HARTA_NOTE_X[1], y1),
                row.keterangan,
                width,
                height,
                size=5.1,
                min_size=3.8,
            )

        if abs(mapping.jumlah_bagian_a) > 0.000001:
            x0, y0, x1, y1 = self._pdf_rect(self.HARTA_TOTAL_RECT, width, height)
            canvas.setFillColor(Color(1.0, 1.0, 0.60))
            canvas.rect(
                x0 + 0.8,
                y0 + 0.8,
                (x1 - x0) - 1.6,
                (y1 - y0) - 1.6,
                stroke=0,
                fill=1,
            )
            canvas.setFillColorRGB(0, 0, 0)
            self._draw_right_money(
                canvas,
                self.HARTA_TOTAL_RECT,
                mapping.jumlah_bagian_a,
                width,
                height,
                size=6.5,
            )

        canvas.save()
        packet.seek(0)
        return packet

    def fill_lampiran_iv(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> LampiranIVMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk membuat Lampiran IV.") from exc

        from core.legacy_1770_lampiran_iii import Legacy1770LampiranIIIService

        with TemporaryDirectory(prefix="tax1770_l4_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_lampiran_iii.pdf"
            previous = Legacy1770LampiranIIIService()
            previous_result = previous.fill_lampiran_iii(
                document,
                base_pdf,
                template_path=template_path,
            )
            if not previous_result.can_fill:
                mapping.issues.append(
                    LampiranIVIssue(
                        "L4_004",
                        "ERROR",
                        "Induk/Lampiran I/Lampiran II/Lampiran III gagal dibentuk sebelum Lampiran IV.",
                    )
                )
                return mapping

            reader = PdfReader(str(base_pdf))
            if len(reader.pages) != 6:
                raise ValueError("Master/output 1770 harus tepat 6 halaman.")

            overlay_page = PdfReader(
                self._make_overlay(reader.pages[self.PAGE_INDEX], document, mapping)
            ).pages[0]
            reader.pages[self.PAGE_INDEX].merge_page(overlay_page)

            writer = PdfWriter()
            for pdf_page in reader.pages:
                writer.add_page(pdf_page)

            target = Path(output_path)
            if target.suffix.lower() != ".pdf":
                target = target.with_suffix(".pdf")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                writer.write(handle)

        return mapping
