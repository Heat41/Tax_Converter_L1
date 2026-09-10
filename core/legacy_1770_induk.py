from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from core.legacy_1770 import Legacy1770Document
from core.legacy_pdf_template import Legacy1770TemplateManager


Rect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class IndukMappingIssue:
    code: str
    severity: str
    message: str


@dataclass
class IndukFieldMappingResult:
    fields: Dict[str, str] = field(default_factory=dict)
    issues: List[IndukMappingIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[IndukMappingIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def can_fill(self) -> bool:
        return not self.errors


class Legacy1770IndukService:
    """Stage 8C.4 - cetak Induk 1770 secara statis pada master bersih 6 halaman."""

    INDUK_PAGE_INDEX = 0
    BASE_WIDTH = 612.0
    BASE_HEIGHT = 936.0

    YEAR_RECT: Rect = (432.58, 21.26, 547.92, 39.26)
    PERIOD_START_RECT: Rect = (432.58, 48.26, 490.30, 64.10)
    PERIOD_END_RECT: Rect = (504.58, 48.26, 562.80, 64.10)

    NPWP_GROUP_RECTS: Sequence[Rect] = (
        (216.53, 119.42, 274.25, 133.10),
        (288.53, 119.42, 346.27, 133.10),
        (360.55, 119.42, 418.27, 133.10),
        (432.58, 119.42, 490.30, 133.10),
    )
    NAME_RECT: Rect = (216.53, 134.54, 547.92, 148.22)

    DECLARATION_NAME_RECT: Rect = (104.16, 864.60, 418.27, 878.28)
    DECLARATION_NPWP_GROUP_RECTS: Sequence[Rect] = (
        (104.04, 880.20, 159.02, 893.88),
        (173.30, 880.20, 231.05, 893.88),
        (245.33, 880.20, 303.05, 893.88),
        (317.33, 880.20, 375.07, 893.88),
    )

    # Fine-tuned langsung dari master bersih/render aktual. Digit tanggungan
    # (contoh TK/0) harus berada DI DALAM kotak kecil setelah label TK/K/K-I.
    PTKP_STATUS_RECTS: Dict[str, Rect] = {
        "TK": (221.0, 420.5, 237.0, 436.3),
        "K": (268.6, 420.5, 284.5, 436.3),
        "KI": (317.4, 420.5, 333.3, 436.3),
    }

    SIGN_16_RECTS: Sequence[Rect] = (
        (103.50, 537.30, 118.80, 548.60),
        (103.50, 549.00, 118.80, 560.30),
    )
    SIGN_19_RECTS: Sequence[Rect] = (
        (118.20, 622.70, 132.90, 633.40),
        (118.20, 634.00, 132.90, 644.70),
    )

    ROW_RECTS: Dict[str, Rect] = {
        "2": (446.98, 269.69, 567.72, 286.13),
        "3": (446.98, 288.05, 567.72, 304.49),
        "5": (446.98, 323.69, 567.72, 340.61),
        "6": (446.98, 342.05, 567.72, 358.97),
        "7": (446.98, 360.41, 567.72, 376.85),
        "9": (446.98, 400.51, 567.72, 416.95),
        "10": (446.98, 418.87, 567.72, 434.23),
        "11": (446.98, 436.15, 567.72, 453.07),
        "12": (446.98, 458.95, 567.72, 475.87),
        "14": (446.98, 496.15, 567.72, 512.59),
        "15": (446.98, 514.63, 567.72, 535.75),
        "16": (446.98, 537.79, 567.72, 558.79),
        "18": (446.98, 599.50, 567.72, 615.94),
        "19": (446.98, 622.90, 567.72, 643.90),
    }

    DECLARATION_WP_RECT: Rect = (103.7, 841.8, 118.4, 855.2)

    @staticmethod
    def _number(value: object) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        if abs(number - round(number)) < 0.000001:
            return str(int(round(number)))
        return (f"{number:.2f}").rstrip("0").rstrip(".")

    @classmethod
    def _number_or_blank(cls, value: object) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        return "" if abs(number) < 0.000001 else cls._number(number)

    @staticmethod
    def _rupiah(value: object) -> str:
        try:
            number = int(round(float(value or 0)))
        except (TypeError, ValueError):
            return ""
        if number == 0:
            return ""
        sign = "-" if number < 0 else ""
        return sign + f"{abs(number):,}".replace(",", ".")

    def map_document(self, document: Legacy1770Document) -> IndukFieldMappingResult:
        result = IndukFieldMappingResult()
        if not document.npwp:
            result.issues.append(IndukMappingIssue("INDUK_001", "ERROR", "NPWP FINAL tidak tersedia."))
        if not document.nama_wp:
            result.issues.append(IndukMappingIssue("INDUK_002", "ERROR", "Nama WP FINAL tidak tersedia."))
        if not document.tahun_pajak:
            result.issues.append(IndukMappingIssue("INDUK_003", "ERROR", "Tahun Pajak FINAL tidak tersedia."))
        if result.errors:
            return result

        pekerjaan = float(document.total_netto_bupot or 0)
        lainnya = float(document.penghasilan_neto_lainnya or 0)
        jumlah_neto = pekerjaan + lainnya
        neto_setelah_zakat = jumlah_neto - float(document.zakat or 0)
        pph_kurang_lebih_16 = float(document.pph_terutang or 0) - float(document.kredit_pajak or 0)
        pph_kurang_lebih_19 = pph_kurang_lebih_16 - float(document.pph25 or 0)

        result.fields = {
            "NPWP": str(document.npwp),
            "Nama Wajib Pajak": str(document.nama_wp),
            "Tahun Pajak": str(document.tahun_pajak),
            "JumlahBagianCinduk": self._number_or_blank(pekerjaan),
            "JumlahBagianD": self._number_or_blank(lainnya),
            "PNInduk": self._number_or_blank(jumlah_neto),
            "ZakatSumbanganWajib": self._number_or_blank(document.zakat),
            "PNsetelahZakat": self._number_or_blank(neto_setelah_zakat),
            "PNsetelahKompen": self._number_or_blank(neto_setelah_zakat),
            "PTKP": self._number_or_blank(document.ptkp),
            "PhKP": self._number_or_blank(document.pkp),
            "PPhTerutang": self._number_or_blank(document.pph_terutang),
            "JumlahPPhTerutang": self._number_or_blank(document.pph_terutang),
            "IIJBAinduk": self._number_or_blank(document.kredit_pajak),
            "PPhLebihKurang": self._number_or_blank(pph_kurang_lebih_16),
            "PPh25": self._number_or_blank(document.pph25),
            "JumlahPPh25": self._number_or_blank(document.pph25),
            "PPhLebihKurangDibayar": self._number_or_blank(pph_kurang_lebih_19),
        }
        result.issues.append(IndukMappingIssue(
            "INDUK_W01", "WARNING",
            "Penghasilan neto usaha non-final belum memiliki sumber domain tersendiri; angka 1 dibiarkan kosong. UMKM final akan masuk Lampiran III.",
        ))
        result.issues.append(IndukMappingIssue(
            "INDUK_W02", "WARNING",
            "Kompensasi kerugian belum dimodelkan; angka 8 dibiarkan kosong dan angka 9 meneruskan angka 7.",
        ))
        return result

    @classmethod
    def _to_reportlab_rect(cls, rect: Rect, width: float, height: float) -> Rect:
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        x0, y0, x1, y1 = rect
        return (x0 * sx, height - (y1 * sy), x1 * sx, height - (y0 * sy))

    @staticmethod
    def _baseline(rect: Rect, font_size: float) -> float:
        x0, y0, x1, y1 = rect
        return y0 + ((y1 - y0 - font_size) / 2.0) + 1.6

    @classmethod
    def _draw_right(cls, canvas, rect: Rect, text: str, width: float, height: float, font_size: float = 8.0) -> None:
        if not text:
            return
        target = cls._to_reportlab_rect(rect, width, height)
        canvas.setFont("Helvetica", font_size * (height / cls.BASE_HEIGHT))
        canvas.drawRightString(target[2] - (3.5 * width / cls.BASE_WIDTH), cls._baseline(target, font_size), text)

    @classmethod
    def _draw_left(cls, canvas, rect: Rect, text: str, width: float, height: float, font_size: float = 7.2) -> None:
        if not text:
            return
        target = cls._to_reportlab_rect(rect, width, height)
        canvas.setFont("Helvetica", font_size * (height / cls.BASE_HEIGHT))
        canvas.drawString(target[0] + (2.0 * width / cls.BASE_WIDTH), cls._baseline(target, font_size), text)

    @classmethod
    def _draw_center(cls, canvas, rect: Rect, text: str, width: float, height: float, font_size: float = 7.2, bold: bool = True) -> None:
        if not text:
            return
        target = cls._to_reportlab_rect(rect, width, height)
        canvas.setFont("Helvetica-Bold" if bold else "Helvetica", font_size * (height / cls.BASE_HEIGHT))
        canvas.drawCentredString((target[0] + target[2]) / 2.0, cls._baseline(target, font_size), text)

    @classmethod
    def _draw_four_group_comb(cls, canvas, groups: Sequence[Rect], text: str, width: float, height: float, *, font_size: float = 7.4) -> None:
        chars = [ch for ch in str(text or "") if ch.isdigit()]
        if not chars:
            return
        index = 0
        for group_rect in groups:
            target = cls._to_reportlab_rect(group_rect, width, height)
            cell_width = (target[2] - target[0]) / 4.0
            canvas.setFont("Helvetica", font_size * (height / cls.BASE_HEIGHT))
            y = cls._baseline(target, font_size)
            for cell in range(4):
                if index >= len(chars):
                    return
                canvas.drawCentredString(target[0] + (cell_width * (cell + 0.5)), y, chars[index])
                index += 1

    @classmethod
    def _draw_year_four_digits(cls, canvas, rect: Rect, year: int, width: float, height: float) -> None:
        digits = f"{int(year):04d}"[-4:]
        target = cls._to_reportlab_rect(rect, width, height)
        cell_width = (target[2] - target[0]) / 4.0
        canvas.setFont("Helvetica-Bold", 9.0 * (height / cls.BASE_HEIGHT))
        y = cls._baseline(target, 9.0)
        for index, digit in enumerate(digits):
            canvas.drawCentredString(target[0] + cell_width * (index + 0.5), y, digit)

    @classmethod
    def _draw_period_four_digits(cls, canvas, rect: Rect, month: int, year: int, width: float, height: float) -> None:
        text = f"{int(month):02d}{int(year) % 100:02d}"
        target = cls._to_reportlab_rect(rect, width, height)
        cell_width = (target[2] - target[0]) / 4.0
        canvas.setFont("Helvetica", 6.2 * (height / cls.BASE_HEIGHT))
        y = cls._baseline(target, 6.2)
        for index, digit in enumerate(text):
            canvas.drawCentredString(target[0] + cell_width * (index + 0.5), y, digit)

    @classmethod
    def _draw_ptkp_status(cls, canvas, status: str, width: float, height: float) -> None:
        normalized = str(status or "").upper().replace(" ", "")
        if not normalized:
            return
        if normalized.startswith("K/I/"):
            key = "KI"
        elif normalized.startswith("K/"):
            key = "K"
        else:
            key = "TK"
        dependent = "".join(ch for ch in normalized.split("/")[-1] if ch.isdigit())[:1]
        if dependent:
            cls._draw_center(canvas, cls.PTKP_STATUS_RECTS[key], dependent, width, height, 6.2, bold=False)

    @classmethod
    def _draw_sign(cls, canvas, rects: Sequence[Rect], value: float, width: float, height: float) -> None:
        if abs(float(value or 0)) < 0.000001:
            return
        target = rects[0] if value > 0 else rects[1]
        cls._draw_center(canvas, target, "X", width, height, 7.0, bold=True)

    def _make_induk_overlay(self, page, document: Legacy1770Document):
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk mencetak Form 1770 statis. Install dengan: python -m pip install reportlab") from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        c = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        self._draw_year_four_digits(c, self.YEAR_RECT, document.tahun_pajak, width, height)
        self._draw_period_four_digits(c, self.PERIOD_START_RECT, 1, document.tahun_pajak, width, height)
        self._draw_period_four_digits(c, self.PERIOD_END_RECT, 12, document.tahun_pajak, width, height)
        self._draw_four_group_comb(c, self.NPWP_GROUP_RECTS, document.npwp, width, height)
        self._draw_left(c, self.NAME_RECT, str(document.nama_wp).upper(), width, height, 7.3)
        self._draw_left(c, self.DECLARATION_NAME_RECT, str(document.nama_wp).upper(), width, height, 7.1)
        self._draw_four_group_comb(c, self.DECLARATION_NPWP_GROUP_RECTS, document.npwp, width, height, font_size=7.2)
        self._draw_center(c, self.DECLARATION_WP_RECT, "X", width, height, 7.0, bold=True)

        pekerjaan = float(document.total_netto_bupot or 0)
        lainnya = float(document.penghasilan_neto_lainnya or 0)
        jumlah_neto = pekerjaan + lainnya
        neto_setelah_zakat = jumlah_neto - float(document.zakat or 0)
        kurang_lebih_16 = float(document.pph_terutang or 0) - float(document.kredit_pajak or 0)
        kredit_sendiri = float(document.pph25 or 0)
        kurang_lebih_19 = kurang_lebih_16 - kredit_sendiri

        row_values = {
            "2": pekerjaan, "3": lainnya, "5": jumlah_neto, "6": document.zakat,
            "7": neto_setelah_zakat, "9": neto_setelah_zakat, "10": document.ptkp,
            "11": document.pkp, "12": document.pph_terutang, "14": document.pph_terutang,
            "15": document.kredit_pajak, "16": abs(kurang_lebih_16), "18": kredit_sendiri,
            "19": abs(kurang_lebih_19),
        }
        for row, value in row_values.items():
            self._draw_right(c, self.ROW_RECTS[row], self._rupiah(value), width, height)

        self._draw_ptkp_status(c, document.status_ptkp, width, height)
        self._draw_sign(c, self.SIGN_16_RECTS, kurang_lebih_16, width, height)
        self._draw_sign(c, self.SIGN_19_RECTS, kurang_lebih_19, width, height)

        c.save()
        packet.seek(0)
        return packet

    @staticmethod
    def _strip_interactive_features(writer) -> None:
        for page in writer.pages:
            for key in ("/Annots", "/AA"):
                if key in page:
                    del page[key]
        root = writer.root_object
        for key in ("/AcroForm", "/OpenAction", "/AA"):
            if key in root:
                del root[key]
        names = root.get("/Names")
        try:
            names_obj = names.get_object() if names is not None else None
            if names_obj is not None and "/JavaScript" in names_obj:
                del names_obj["/JavaScript"]
        except (AttributeError, TypeError):
            pass

    def fill_induk(self, document: Legacy1770Document, output_path: str | Path, *, template_path: Optional[str | Path] = None) -> IndukFieldMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping
        manager = Legacy1770TemplateManager(template_path)
        info = manager.require_ready()
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk membuat Form 1770. Install dengan: python -m pip install pypdf") from exc
        reader = PdfReader(str(info.path))
        if len(reader.pages) != 6:
            raise ValueError("Master bersih 1770 harus tepat 6 halaman.")
        source_induk = reader.pages[self.INDUK_PAGE_INDEX]
        overlay_stream = self._make_induk_overlay(source_induk, document)
        overlay_page = PdfReader(overlay_stream).pages[0]
        source_induk.merge_page(overlay_page)
        writer = PdfWriter()
        for source_page in reader.pages:
            writer.add_page(source_page)
        self._strip_interactive_features(writer)
        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)
        return mapping
