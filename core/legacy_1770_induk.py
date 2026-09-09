from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from core.legacy_1770 import Legacy1770Document
from core.legacy_pdf_template import Legacy1770TemplateManager


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
    """Stage 8C.4 - cetak statis data FINAL ke bentuk Form 1770 lama.

    AcroForm template hanya dipakai untuk membaca posisi kotak. Nilai akhir tidak
    diisi melalui field interaktif karena appearance AcroForm dapat bergeser,
    menduplikasi field bernama sama, dan berbeda antar PDF viewer. Nilai dicetak
    langsung pada koordinat kotak asli, lalu seluruh annotation/form dibuang.
    """

    INDONESIAN_INDUK_PAGE_INDEX = 9

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
            number = 0
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
        neto_setelah_kompensasi = neto_setelah_zakat
        pph_kurang_lebih_16 = float(document.pph_terutang or 0) - float(document.kredit_pajak or 0)
        pph_kurang_lebih_19 = pph_kurang_lebih_16 - float(document.pph25 or 0)

        # Nama field sesuai posisi sebenarnya pada template resmi.
        # JumlahBagianCinduk = angka 2, PNInduk = angka 5, PhKP = angka 11.
        result.fields = {
            "NPWP": str(document.npwp),
            "Nama Wajib Pajak": str(document.nama_wp),
            "Tahun Pajak": str(document.tahun_pajak),
            "JumlahBagianCinduk": self._number_or_blank(pekerjaan),
            "JumlahBagianD": self._number_or_blank(lainnya),
            "PNInduk": self._number_or_blank(jumlah_neto),
            "ZakatSumbanganWajib": self._number_or_blank(document.zakat),
            "PNsetelahZakat": self._number_or_blank(neto_setelah_zakat),
            "PNsetelahKompen": self._number_or_blank(neto_setelah_kompensasi),
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

        result.issues.append(
            IndukMappingIssue(
                "INDUK_W01",
                "WARNING",
                "Penghasilan neto usaha non-final belum memiliki sumber domain tersendiri; angka 1 dibiarkan kosong. UMKM final akan masuk Lampiran III.",
            )
        )
        result.issues.append(
            IndukMappingIssue(
                "INDUK_W02",
                "WARNING",
                "Kompensasi kerugian belum dimodelkan; angka 8 dibiarkan kosong dan angka 9 meneruskan angka 7.",
            )
        )
        return result

    @staticmethod
    def _widget_field_name(widget) -> Optional[str]:
        current = widget
        for _ in range(6):
            value = current.get("/T")
            if value is not None:
                return str(value)
            parent = current.get("/Parent")
            if parent is None:
                return None
            current = parent.get_object()
        return None

    @classmethod
    def _field_rects(cls, page, field_name: str) -> List[List[float]]:
        result: List[List[float]] = []
        for ref in page.get("/Annots", []) or []:
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            if cls._widget_field_name(widget) != field_name:
                continue
            rect = widget.get("/Rect")
            if rect:
                result.append([float(v) for v in rect])
        return result

    @classmethod
    def _button_rect_by_export(cls, page, field_name: str, export_name: str) -> Optional[List[float]]:
        wanted = "/" + export_name.lstrip("/")
        for ref in page.get("/Annots", []) or []:
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            if cls._widget_field_name(widget) != field_name:
                continue
            normal = (widget.get("/AP") or {}).get("/N")
            if isinstance(normal, dict) and wanted in normal:
                return [float(v) for v in widget.get("/Rect")]
        return None

    @staticmethod
    def _baseline(rect: List[float], font_size: float) -> float:
        return rect[1] + ((rect[3] - rect[1] - font_size) / 2.0) + 1.8

    @classmethod
    def _draw_right(cls, canvas, rect: Optional[List[float]], text: str, font_size: float = 8.2) -> None:
        if not rect or not text:
            return
        canvas.setFont("Helvetica", font_size)
        canvas.drawRightString(rect[2] - 4.0, cls._baseline(rect, font_size), text)

    @classmethod
    def _draw_left(cls, canvas, rect: Optional[List[float]], text: str, font_size: float = 7.8) -> None:
        if not rect or not text:
            return
        canvas.setFont("Helvetica", font_size)
        canvas.drawString(rect[0] + 2.0, cls._baseline(rect, font_size), text)

    @classmethod
    def _draw_center(cls, canvas, rect: Optional[List[float]], text: str, font_size: float = 7.5) -> None:
        if not rect or not text:
            return
        canvas.setFont("Helvetica-Bold", font_size)
        x = (rect[0] + rect[2]) / 2.0
        canvas.drawCentredString(x, cls._baseline(rect, font_size), text)

    @classmethod
    def _draw_npwp_comb(cls, canvas, rect: Optional[List[float]], npwp: str) -> None:
        if not rect:
            return
        digits = "".join(ch for ch in str(npwp or "") if ch.isdigit())[:16]
        if not digits:
            return

        # Pola kotak NPWP lama: 2-3-3-1-3-3-1 digit.
        groups = (2, 3, 3, 1, 3, 3, 1)
        box_width = 12.0
        total_boxes = sum(groups)
        usable = rect[2] - rect[0]
        gap = max(0.0, (usable - (total_boxes * box_width)) / (len(groups) - 1))
        x = rect[0]
        index = 0
        canvas.setFont("Helvetica", 7.3)
        y = cls._baseline(rect, 7.3)
        for gi, count in enumerate(groups):
            for _ in range(count):
                if index >= len(digits):
                    return
                canvas.drawCentredString(x + (box_width / 2.0), y, digits[index])
                x += box_width
                index += 1
            if gi < len(groups) - 1:
                x += gap

    @classmethod
    def _draw_year(cls, canvas, rect: Optional[List[float]], year: int) -> None:
        if not rect:
            return
        suffix = f"{int(year):04d}"[-2:]
        width = rect[2] - rect[0]
        half = width / 2.0
        canvas.setFont("Helvetica-Bold", 9.0)
        y = cls._baseline(rect, 9.0)
        canvas.drawCentredString(rect[0] + (half * 0.5), y, suffix[0])
        canvas.drawCentredString(rect[0] + (half * 1.5), y, suffix[1])

    @classmethod
    def _draw_ptkp_status(cls, canvas, page, status: str) -> None:
        normalized = str(status or "").upper().replace(" ", "")
        if not normalized:
            return
        if normalized.startswith("K/I/"):
            category, dependent = "KI", normalized.split("/")[-1]
            combo_field = "ComKI"
        elif normalized.startswith("K/"):
            category, dependent = "K", normalized.split("/")[-1]
            combo_field = "ComK"
        else:
            category, dependent = "TK", normalized.split("/")[-1]
            combo_field = "ComTK"

        rect = cls._button_rect_by_export(page, "RbPtkp", category)
        cls._draw_center(canvas, rect, "X", 6.8)
        combo_rects = cls._field_rects(page, combo_field)
        if combo_rects:
            cls._draw_center(canvas, combo_rects[0], dependent, 7.0)

    @classmethod
    def _draw_sign_choice(cls, canvas, page, field_name: str, value: float) -> None:
        rects = cls._field_rects(page, field_name)
        if len(rects) < 2:
            return
        target = rects[0] if value >= 0 else rects[1]
        cls._draw_center(canvas, target, "X", 6.8)

    def _make_induk_overlay(self, page, document: Legacy1770Document):
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError(
                "Library reportlab diperlukan untuk mencetak Form 1770 statis. "
                "Install dengan: python -m pip install reportlab"
            ) from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        c = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        year_rects = self._field_rects(page, "Tahun Pajak")
        if year_rects:
            self._draw_year(c, year_rects[0], document.tahun_pajak)

        npwp_rects = self._field_rects(page, "NPWP")
        for rect in npwp_rects:
            self._draw_npwp_comb(c, rect, document.npwp)

        name_rects = self._field_rects(page, "Nama Wajib Pajak")
        for rect in name_rects:
            self._draw_left(c, rect, str(document.nama_wp).upper(), 7.3)

        jumlah_neto = float(document.total_netto_bupot or 0) + float(document.penghasilan_neto_lainnya or 0)
        neto_setelah_zakat = jumlah_neto - float(document.zakat or 0)
        kurang_lebih_16 = float(document.pph_terutang or 0) - float(document.kredit_pajak or 0)
        kurang_lebih_19 = kurang_lebih_16 - float(document.pph25 or 0)

        numeric_fields = {
            "JumlahBagianCinduk": document.total_netto_bupot,
            "JumlahBagianD": document.penghasilan_neto_lainnya,
            "PNInduk": jumlah_neto,
            "ZakatSumbanganWajib": document.zakat,
            "PNsetelahZakat": neto_setelah_zakat,
            "PNsetelahKompen": neto_setelah_zakat,
            "PTKP": document.ptkp,
            "PhKP": document.pkp,
            "PPhTerutang": document.pph_terutang,
            "JumlahPPhTerutang": document.pph_terutang,
            "IIJBAinduk": document.kredit_pajak,
            "PPhLebihKurang": kurang_lebih_16,
            "PPh25": document.pph25,
            "JumlahPPh25": document.pph25,
            "PPhLebihKurangDibayar": kurang_lebih_19,
        }
        for field_name, value in numeric_fields.items():
            rects = self._field_rects(page, field_name)
            if rects:
                self._draw_right(c, rects[0], self._rupiah(value))

        self._draw_ptkp_status(c, page, document.status_ptkp)
        self._draw_sign_choice(c, page, "14-15", kurang_lebih_16)
        self._draw_sign_choice(c, page, "16-18", kurang_lebih_19)

        c.save()
        packet.seek(0)
        return packet

    @staticmethod
    def _strip_interactive_page(page) -> None:
        for key in ("/Annots", "/AA"):
            if key in page:
                del page[key]

    def fill_induk(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> IndukFieldMappingResult:
        mapping = self.map_document(document)
        if not mapping.can_fill:
            return mapping

        manager = Legacy1770TemplateManager(template_path)
        info = manager.require_ready()

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf diperlukan untuk membuat Form 1770. Install dengan: python -m pip install pypdf"
            ) from exc

        reader = PdfReader(str(info.path))
        source_induk = reader.pages[self.INDONESIAN_INDUK_PAGE_INDEX]

        overlay_stream = self._make_induk_overlay(source_induk, document)
        overlay_page = PdfReader(overlay_stream).pages[0]
        source_induk.merge_page(overlay_page)

        writer = PdfWriter()
        for page_number in manager.INDONESIAN_EXPORT_PAGES:
            source_index = int(page_number) - 1
            source_page = reader.pages[source_index]
            self._strip_interactive_page(source_page)
            writer.add_page(source_page)

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

        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)

        return mapping
