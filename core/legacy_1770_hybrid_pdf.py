from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from core.legacy_1770 import Legacy1770Document, Legacy1770DocumentService
from core.legacy_1770_static_pdf import Legacy1770StaticPdfService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


@dataclass(frozen=True)
class HybridPdfIssue:
    code: str
    severity: str
    message: str


@dataclass
class HybridPdfResult:
    output_path: Path
    page_count: int = 0
    size_bytes: int = 0
    sha256: str = ""
    issues: List[HybridPdfIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[HybridPdfIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def ok(self) -> bool:
        return not self.errors and self.output_path.is_file() and self.page_count >= 6


class Legacy1770HybridPdfService:
    """Ekspor PDF HYBRID 1770 satu arah.

    Boundary format dikunci:
    - halaman 1: Induk H1 format baru;
    - halaman 2: Induk H2 format baru;
    - halaman berikutnya: format lama, dimulai dari Lampiran I Halaman 2.

    Bagian legacy tidak digambar ulang. Service memakai engine PDF lama yang
    sudah dikalibrasi, kemudian membuang halaman master lama sebelum
    Lampiran I Halaman 2. Dengan demikian visual Lampiran I H2 s.d Lampiran IV
    tetap berasal dari renderer legacy yang sama dengan output lama.
    """

    LEGAL_SIZE = (612.0, 936.0)
    LEGACY_START_INDEX = 2  # master lama: 0=Induk, 1=Lamp I H1, 2=Lamp I H2

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = db_path

    @staticmethod
    def _money(value) -> str:
        try:
            number = int(round(float(value or 0)))
        except (TypeError, ValueError):
            number = 0
        return f"{number:,}".replace(",", ".")

    @staticmethod
    def _draw_text(canvas, x, y, text, *, size=8, bold=False):
        canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        canvas.drawString(x, y, str(text or ""))

    @classmethod
    def _draw_section_title(cls, canvas, y: float, title: str) -> float:
        canvas.setFillColorRGB(0.88, 0.93, 0.97)
        canvas.rect(28, y - 16, 556, 18, fill=1, stroke=1)
        canvas.setFillColorRGB(0, 0, 0)
        cls._draw_text(canvas, 34, y - 10, title, size=8.2, bold=True)
        return y - 24

    @classmethod
    def _draw_field(cls, canvas, y: float, no: str, label: str, value="") -> float:
        canvas.rect(28, y - 18, 556, 20, fill=0, stroke=1)
        cls._draw_text(canvas, 34, y - 11, no, size=7)
        cls._draw_text(canvas, 62, y - 11, label[:78], size=7)
        canvas.setFillColorRGB(1.0, 0.95, 0.75)
        canvas.rect(454, y - 17, 129, 18, fill=1, stroke=1)
        canvas.setFillColorRGB(0, 0, 0)
        cls._draw_text(canvas, 460, y - 11, value, size=7, bold=True)
        return y - 20

    @classmethod
    def _draw_new_header(cls, canvas, document: Legacy1770Document, page_no: int) -> float:
        width, height = cls.LEGAL_SIZE
        canvas.setFillColorRGB(0.12, 0.31, 0.47)
        canvas.rect(28, height - 62, width - 56, 34, fill=1, stroke=0)
        canvas.setFillColorRGB(1, 1, 1)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(width / 2, height - 43, "SPT TAHUNAN PPh WAJIB PAJAK ORANG PRIBADI")
        canvas.setFillColorRGB(0, 0, 0)
        cls._draw_text(canvas, 28, height - 78, "KEMENTERIAN KEUANGAN RI - DIREKTORAT JENDERAL PAJAK", size=7.5, bold=True)
        cls._draw_text(canvas, 28, height - 96, "INDUK", size=10, bold=True)
        cls._draw_text(canvas, 500, height - 96, f"HALAMAN {page_no}", size=9, bold=True)
        cls._draw_text(canvas, 28, height - 116, f"TAHUN PAJAK: {document.tahun_pajak}", size=8, bold=True)
        cls._draw_text(canvas, 220, height - 116, "PERIODE: 01 s.d 12", size=8, bold=True)
        cls._draw_text(canvas, 420, height - 116, "STATUS: NORMAL", size=8, bold=True)
        return height - 140

    @classmethod
    def _render_new_pages(cls, document: Legacy1770Document, target: Path) -> None:
        try:
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError("Library reportlab diperlukan untuk ekspor PDF HYBRID.") from exc

        target.parent.mkdir(parents=True, exist_ok=True)
        canvas = reportlab_canvas.Canvas(str(target), pagesize=cls.LEGAL_SIZE)

        # Halaman 1 - A s.d D
        y = cls._draw_new_header(canvas, document, 1)
        y = cls._draw_section_title(canvas, y, "A. IDENTITAS WAJIB PAJAK")
        y = cls._draw_field(canvas, y, "1", "NIK/NPWP", document.npwp)
        y = cls._draw_field(canvas, y, "2", "Nama", document.nama_wp.upper())
        y = cls._draw_field(canvas, y, "3", "Status PTKP", document.status_ptkp)

        y = cls._draw_section_title(canvas, y - 5, "B. IKHTISAR PENGHASILAN NETO")
        y = cls._draw_field(canvas, y, "1a", "Penghasilan neto dari pekerjaan", cls._money(document.total_netto_bupot))
        y = cls._draw_field(canvas, y, "1b", "Penghasilan neto usaha/pekerjaan bebas", "0")
        y = cls._draw_field(canvas, y, "1c", "Penghasilan neto dalam negeri lainnya", cls._money(document.penghasilan_neto_lainnya))
        y = cls._draw_field(canvas, y, "1d", "Penghasilan luar negeri", "0")

        y = cls._draw_section_title(canvas, y - 5, "C. PERHITUNGAN PPh TERUTANG")
        y = cls._draw_field(canvas, y, "2", "Penghasilan neto gabungan", cls._money(document.penghasilan_neto_gabungan))
        y = cls._draw_field(canvas, y, "3", "Zakat/sumbangan keagamaan wajib", cls._money(document.zakat))
        y = cls._draw_field(canvas, y, "5", "Penghasilan Tidak Kena Pajak", cls._money(document.ptkp))
        y = cls._draw_field(canvas, y, "6", "Penghasilan Kena Pajak", cls._money(document.pkp))
        y = cls._draw_field(canvas, y, "7", "PPh terutang", cls._money(document.pph_terutang))

        y = cls._draw_section_title(canvas, y - 5, "D. KREDIT PAJAK")
        y = cls._draw_field(canvas, y, "10a", "PPh dipotong/dipungut pihak lain", cls._money(document.kredit_pajak))
        cls._draw_field(canvas, y, "10b", "Angsuran PPh Pasal 25", cls._money(document.pph25))
        canvas.showPage()

        # Halaman 2 - E s.d K
        y = cls._draw_new_header(canvas, document, 2)
        y = cls._draw_section_title(canvas, y, "E. PPh KURANG/LEBIH BAYAR")
        y = cls._draw_field(canvas, y, "11a", "PPh kurang/lebih bayar", cls._money(document.kurang_lebih_bayar))

        y = cls._draw_section_title(canvas, y - 5, "F. PEMBETULAN")
        y = cls._draw_field(canvas, y, "12a", "PPh kurang/lebih bayar pada SPT yang dibetulkan", "")
        y = cls._draw_field(canvas, y, "12b", "PPh kurang/lebih bayar karena pembetulan", "")

        y = cls._draw_section_title(canvas, y - 5, "G. PERMOHONAN PENGEMBALIAN PPh LEBIH BAYAR")
        y = cls._draw_field(canvas, y, "", "Permohonan pengembalian", "")

        y = cls._draw_section_title(canvas, y - 5, "H. ANGSURAN PPh PASAL 25 TAHUN PAJAK BERIKUTNYA")
        y = cls._draw_field(canvas, y, "13a", "Angsuran PPh Pasal 25", cls._money(document.pph25))

        y = cls._draw_section_title(canvas, y - 5, "I. PERNYATAAN TRANSAKSI LAINNYA")
        total_harta = sum(float(row.nilai_tahun_berjalan or 0) for row in document.harta_rows)
        final_income = float(document.umkm_bruto or 0) + sum(float(row.dpp or 0) for row in document.penghasilan_final_lainnya)
        y = cls._draw_field(canvas, y, "14a", "Harta pada akhir Tahun Pajak", cls._money(total_harta))
        y = cls._draw_field(canvas, y, "14c", "Penghasilan dikenakan PPh Final", cls._money(final_income))
        y = cls._draw_field(canvas, y, "14d", "Penghasilan yang tidak termasuk objek pajak", cls._money(document.penghasilan_bukan_objek))

        y = cls._draw_section_title(canvas, y - 5, "J. LAMPIRAN TAMBAHAN")
        y = cls._draw_field(canvas, y, "15", "Lampiran/dokumen pendukung", "")

        y = cls._draw_section_title(canvas, y - 5, "K. PERNYATAAN")
        cls._draw_field(canvas, y, "", "Nama Wajib Pajak / Penandatangan", document.nama_wp.upper())
        canvas.save()

    @classmethod
    def _merge_hybrid(cls, new_pages: Path, legacy_pdf: Path, target: Path) -> int:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk ekspor PDF HYBRID.") from exc

        new_reader = PdfReader(str(new_pages))
        legacy_reader = PdfReader(str(legacy_pdf))
        if len(new_reader.pages) != 2:
            raise RuntimeError("Renderer format baru harus menghasilkan tepat 2 halaman.")
        if len(legacy_reader.pages) <= cls.LEGACY_START_INDEX:
            raise RuntimeError("PDF legacy tidak memiliki Lampiran I Halaman 2.")

        writer = PdfWriter()
        writer.add_page(new_reader.pages[0])
        writer.add_page(new_reader.pages[1])
        for page in legacy_reader.pages[cls.LEGACY_START_INDEX:]:
            writer.add_page(page)

        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)
        return len(writer.pages)

    @classmethod
    def inspect(cls, path: str | Path) -> HybridPdfResult:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Library pypdf diperlukan untuk memverifikasi PDF HYBRID.") from exc

        target = Path(path)
        result = HybridPdfResult(output_path=target)
        if not target.is_file():
            result.issues.append(HybridPdfIssue("HPDF_001", "ERROR", "File PDF HYBRID tidak ditemukan."))
            return result

        data = target.read_bytes()
        result.size_bytes = len(data)
        result.sha256 = hashlib.sha256(data).hexdigest()
        reader = PdfReader(str(target))
        result.page_count = len(reader.pages)

        if result.page_count < 6:
            result.issues.append(HybridPdfIssue("HPDF_002", "ERROR", "PDF HYBRID harus memiliki sedikitnya 6 halaman."))

        for index, page in enumerate(reader.pages, start=1):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            if abs(width - cls.LEGAL_SIZE[0]) > 2 or abs(height - cls.LEGAL_SIZE[1]) > 2:
                result.issues.append(
                    HybridPdfIssue(
                        "HPDF_003",
                        "ERROR",
                        f"Halaman {index} bukan ukuran Legal ({width:.1f} x {height:.1f}).",
                    )
                )
        return result

    def export_document(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> HybridPdfResult:
        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        if not document.can_export_pdf:
            result = HybridPdfResult(output_path=target)
            if document.errors:
                for issue in document.errors:
                    row_number = getattr(issue, "row_number", None)
                    row_text = f" (baris Harta {row_number})" if row_number else ""
                    result.issues.append(
                        HybridPdfIssue(
                            getattr(issue, "code", "HPDF_004"),
                            "ERROR",
                            f"{getattr(issue, 'message', 'Snapshot FINAL belum siap.')}{row_text}",
                        )
                    )
            else:
                missing = []
                if not document.npwp:
                    missing.append("NPWP")
                if not document.nama_wp:
                    missing.append("Nama WP")
                if not document.tahun_pajak:
                    missing.append("Tahun Pajak")
                detail = ", ".join(missing) if missing else "identitas snapshot"
                result.issues.append(
                    HybridPdfIssue(
                        "HPDF_004",
                        "ERROR",
                        f"Snapshot FINAL belum siap untuk ekspor PDF HYBRID: {detail} belum lengkap.",
                    )
                )
            return result

        with TemporaryDirectory(prefix="tax1770_hybrid_pdf_") as temp_dir:
            temp = Path(temp_dir)
            new_pages = temp / "new_eform_pages.pdf"
            legacy_pdf = temp / "legacy_full.pdf"

            self._render_new_pages(document, new_pages)
            legacy_result = Legacy1770StaticPdfService().finalize_document(
                document,
                legacy_pdf,
                template_path=template_path or DEFAULT_TEMPLATE_PATH,
            )
            if not legacy_result.ok:
                result = HybridPdfResult(output_path=target)
                for issue in legacy_result.issues:
                    result.issues.append(HybridPdfIssue("HPDF_LEGACY", issue.severity, issue.message))
                return result

            self._merge_hybrid(new_pages, legacy_pdf, target)

        return self.inspect(target)

    def export_active_final(
        self,
        npwp: str,
        tahun_pajak: int,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> HybridPdfResult:
        document = Legacy1770DocumentService(db_path=self.db_path).build_active_final(npwp, tahun_pajak)
        return self.export_document(document, output_path, template_path=template_path)
