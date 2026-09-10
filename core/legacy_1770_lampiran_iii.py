from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document, Legacy1770FinalIncomeRow


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class LampiranIIIFinalRow:
    nomor: int
    dpp: float = 0.0
    pph: float = 0.0


@dataclass(frozen=True)
class LampiranIIIIssue:
    code: str
    severity: str
    message: str


@dataclass
class LampiranIIIMappingResult:
    final_rows: List[LampiranIIIFinalRow] = field(default_factory=list)
    jumlah_bagian_a_dpp: float = 0.0
    jumlah_bagian_a_pph: float = 0.0
    bukan_objek_rows: Dict[int, float] = field(default_factory=dict)
    jumlah_bagian_b: float = 0.0
    penghasilan_pasangan_terpisah: float = 0.0
    issues: List[LampiranIIIIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LampiranIIIIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[LampiranIIIIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def can_fill(self) -> bool:
        return not self.errors


class Legacy1770LampiranIIIService:
    """Stage 8C.7 - cetak Lampiran III pada halaman 5 master bersih.

    Header dikalibrasi khusus halaman 5 karena posisi tahun/periode/NPWP/nama
    berbeda beberapa titik dari Lampiran II. Nilai berasal dari snapshot FINAL.
    Data yang belum punya breakdown domain tidak ditebak; nilai agregat ditempatkan
    pada baris umum yang tersedia dan diberi warning pada mapping.
    """

    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0
    PAGE_INDEX = 4

    # Header khusus halaman 5 / Lampiran III, diukur dari master halaman ini.
    YEAR_CELL_CENTERS: Sequence[float] = (468.82, 499.18, 528.82, 559.32)
    YEAR_BASELINE_TOP = 42.55
    YEAR_FONT_SIZE = 15.384

    PERIOD_START_CELL_CENTERS: Sequence[float] = (461.70, 477.42, 492.30, 506.82)
    PERIOD_END_CELL_CENTERS: Sequence[float] = (536.72, 551.84, 567.32, 583.40)
    PERIOD_BASELINE_TOP = 70.75
    PERIOD_FONT_SIZE = 7.704

    NPWP_CELL_CENTERS: Sequence[float] = (
        170.38,
        186.46,
        202.18,
        217.33,
        248.53,
        263.65,
        279.13,
        294.49,
        323.91,
        339.27,
        354.39,
        369.27,
        398.55,
        413.67,
        429.18,
        445.26,
    )
    NPWP_BASELINE_TOP = 142.70
    NPWP_FONT_SIZE = 7.704

    NAME_X = 163.34
    NAME_BASELINE_TOP = 161.20
    NAME_FONT_SIZE = 7.704
    NAME_MAX_X = 572.0

    # Bagian A: baris 1-16 + jumlah 17.
    A_ROW_TOPS: Sequence[Tuple[float, float]] = tuple(
        (222.53 + (23.28 * i), 245.45 + (23.28 * i)) for i in range(16)
    )
    A_DPP_X = (270.77, 436.66)
    A_PPH_X = (436.54, 591.24)
    A_TOTAL_PPH_RECT: Rect = (436.54, 594.70, 591.24, 618.10)

    # Bagian B: 6 baris + total JBB.
    B_ROW_RECTS: Sequence[Rect] = (
        (436.54, 675.34, 591.24, 697.66),
        (436.54, 697.78, 591.24, 720.94),
        (436.54, 721.06, 591.24, 743.02),
        (436.54, 743.14, 591.24, 765.12),
        (436.54, 765.24, 591.24, 787.20),
        (436.54, 787.32, 591.24, 808.08),
    )
    B_TOTAL_RECT: Rect = (436.54, 808.08, 591.24, 827.40)

    # Bagian C belum mempunyai sumber data khusus pada domain saat ini.
    C_VALUE_RECT: Rect = (436.90, 868.68, 591.48, 892.44)

    @staticmethod
    def _classify_final_income(row: Legacy1770FinalIncomeRow) -> int:
        text = " ".join(str(row.keterangan or "").upper().split())
        if any(key in text for key in ("DEPOSITO", "TABUNGAN", "DISKONTO SBI", "SURAT BERHARGA NEGARA", "SBN")):
            return 1
        if "OBLIGASI" in text:
            return 2
        if "SAHAM" in text and ("BURSA" in text or "EFEK" in text):
            return 3
        if "HADIAH" in text and "UNDIAN" in text:
            return 4
        if any(key in text for key in ("PESANGON", "TUNJANGAN HARI TUA", "TEBUSAN PENSIUN", "PENSIUN")):
            return 5
        if "HONORARIUM" in text and any(key in text for key in ("APBN", "APBD")):
            return 6
        if "PENGALIHAN" in text and "TANAH" in text:
            return 7
        if "BANGUN" in text and "GUNA" in text and "SERAH" in text:
            return 8
        if "SEWA" in text and ("TANAH" in text or "BANGUNAN" in text):
            return 9
        if "KONSTRUKSI" in text:
            return 10
        if any(key in text for key in ("BBM", "PENYALUR", "DEALER", "AGEN PRODUK")):
            return 11
        if "KOPERASI" in text and "BUNGA" in text:
            return 12
        if "DERIVATIF" in text:
            return 13
        if "DIVIDEN" in text:
            return 14
        if ("ISTERI" in text or "SUAMI" in text) and "PEMBERI KERJA" in text:
            return 15
        return 16

    def map_document(self, document: Legacy1770Document) -> LampiranIIIMappingResult:
        result = LampiranIIIMappingResult()
        if not document.npwp:
            result.issues.append(LampiranIIIIssue("L3_001", "ERROR", "NPWP FINAL tidak tersedia."))
        if not document.nama_wp:
            result.issues.append(LampiranIIIIssue("L3_002", "ERROR", "Nama WP FINAL tidak tersedia."))
        if not document.tahun_pajak:
            result.issues.append(LampiranIIIIssue("L3_003", "ERROR", "Tahun Pajak FINAL tidak tersedia."))
        if result.errors:
            return result

        buckets: Dict[int, List[float]] = {i: [0.0, 0.0] for i in range(1, 17)}
        for row in document.penghasilan_final_lainnya:
            nomor = self._classify_final_income(row)
            buckets[nomor][0] += float(row.dpp or 0)
            buckets[nomor][1] += float(row.pph or 0)

        # Penghasilan UMKM bersifat final, tetapi domain saat ini belum menyimpan
        # kategori lama yang lebih spesifik. Masukkan ke baris 16 (lainnya/final).
        if abs(float(document.umkm_bruto or 0)) > 0.000001 or abs(float(document.umkm_pph_setor or 0)) > 0.000001:
            buckets[16][0] += float(document.umkm_bruto or 0)
            buckets[16][1] += float(document.umkm_pph_setor or 0)

        result.final_rows = [
            LampiranIIIFinalRow(i, buckets[i][0], buckets[i][1]) for i in range(1, 17)
        ]
        result.jumlah_bagian_a_dpp = sum(item.dpp for item in result.final_rows)
        result.jumlah_bagian_a_pph = sum(item.pph for item in result.final_rows)

        # Snapshot saat ini hanya punya total bukan-objek tanpa breakdown kategori.
        # Supaya tidak menebak apakah hibah/warisan/dll, tempatkan pada baris 6.
        if abs(float(document.penghasilan_bukan_objek or 0)) > 0.000001:
            result.bukan_objek_rows[6] = float(document.penghasilan_bukan_objek)
            result.jumlah_bagian_b = float(document.penghasilan_bukan_objek)
            result.issues.append(
                LampiranIIIIssue(
                    "L3_W01",
                    "WARNING",
                    "Penghasilan bukan objek pada snapshot masih agregat tanpa breakdown; Lampiran III menempatkannya pada baris 6 'Penghasilan lain yang tidak termasuk objek pajak' tanpa menebak jenisnya.",
                )
            )

        # Belum ada field terpisah untuk penghasilan isteri/suami yang dikenakan
        # pajak secara terpisah. Biarkan Bagian C kosong sampai domain tersedia.
        result.penghasilan_pasangan_terpisah = 0.0
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
    def _draw_header(cls, canvas, document: Legacy1770Document, width: float, height: float) -> None:
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

    @classmethod
    def _draw_money(cls, canvas, rect: Rect, value: float, width: float, height: float, *, size: float = 6.6) -> None:
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

    def _make_overlay(self, page, document: Legacy1770Document, mapping: LampiranIIIMappingResult):
        try:
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Lampiran III.") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        canvas = reportlab_canvas.Canvas(packet, pagesize=(width, height))
        self._draw_header(canvas, document, width, height)

        for row in mapping.final_rows:
            if not (1 <= row.nomor <= 16):
                continue
            y0, y1 = self.A_ROW_TOPS[row.nomor - 1]
            self._draw_money(canvas, (self.A_DPP_X[0], y0, self.A_DPP_X[1], y1), row.dpp, width, height)
            self._draw_money(canvas, (self.A_PPH_X[0], y0, self.A_PPH_X[1], y1), row.pph, width, height)

        if abs(mapping.jumlah_bagian_a_pph) > 0.000001:
            x0, y0, x1, y1 = self._pdf_rect(self.A_TOTAL_PPH_RECT, width, height)
            canvas.setFillColor(Color(1.0, 1.0, 0.60))
            canvas.rect(x0 + 0.8, y0 + 0.8, (x1 - x0) - 1.6, (y1 - y0) - 1.6, stroke=0, fill=1)
            canvas.setFillColorRGB(0, 0, 0)
            self._draw_money(canvas, self.A_TOTAL_PPH_RECT, mapping.jumlah_bagian_a_pph, width, height, size=7.0)

        for row_number, value in mapping.bukan_objek_rows.items():
            if 1 <= row_number <= len(self.B_ROW_RECTS):
                self._draw_money(canvas, self.B_ROW_RECTS[row_number - 1], value, width, height)

        if abs(mapping.jumlah_bagian_b) > 0.000001:
            x0, y0, x1, y1 = self._pdf_rect(self.B_TOTAL_RECT, width, height)
            canvas.setFillColor(Color(1.0, 1.0, 0.60))
            canvas.rect(x0 + 0.8, y0 + 0.8, (x1 - x0) - 1.6, (y1 - y0) - 1.6, stroke=0, fill=1)
            canvas.setFillColorRGB(0, 0, 0)
            self._draw_money(canvas, self.B_TOTAL_RECT, mapping.jumlah_bagian_b, width, height, size=7.0)

        if abs(mapping.penghasilan_pasangan_terpisah) > 0.000001:
            self._draw_money(canvas, self.C_VALUE_RECT, mapping.penghasilan_pasangan_terpisah, width, height)

        canvas.save()
        packet.seek(0)
        return packet

    def fill_lampiran_iii(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> LampiranIIIMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk membuat Lampiran III.") from exc

        from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService

        with TemporaryDirectory(prefix="tax1770_l3_") as temp_dir:
            base_pdf = Path(temp_dir) / "base_lampiran_ii.pdf"
            previous = Legacy1770LampiranIIService()
            previous_result = previous.fill_lampiran_ii(document, base_pdf, template_path=template_path)
            if not previous_result.can_fill:
                mapping.issues.append(
                    LampiranIIIIssue(
                        "L3_004",
                        "ERROR",
                        "Induk/Lampiran I/Lampiran II gagal dibentuk sebelum Lampiran III.",
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
            for page in reader.pages:
                writer.add_page(page)

            target = Path(output_path)
            if target.suffix.lower() != ".pdf":
                target = target.with_suffix(".pdf")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                writer.write(handle)

        return mapping
