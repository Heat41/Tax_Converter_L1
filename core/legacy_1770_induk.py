from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.legacy_1770 import Legacy1770Document
from core.legacy_pdf_field_map import INDUK_FIELDS
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
    """Stage 8C.4 - mapping snapshot FINAL ke bentuk statis Form 1770 lama.

    Template resmi hanya dipakai sebagai bentuk/visual. File hasil tidak boleh
    memiliki field AcroForm, JavaScript, tombol, checkbox interaktif, atau fitur
    pengisian PDF lain. Nilai ditanam permanen ke konten halaman (flattened),
    sehingga perilakunya sama seperti PDF contoh lama milik Lisa.
    """

    INDONESIAN_INDUK_PAGE_INDEX = 9  # halaman 10 pada template sumber 16 halaman

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

        values = {
            "npwp": document.npwp,
            "nama_wp": document.nama_wp,
            "tahun_pajak": str(document.tahun_pajak),
            "penghasilan_pekerjaan": self._number_or_blank(pekerjaan),
            "penghasilan_lainnya": self._number_or_blank(lainnya),
            "zakat": self._number_or_blank(document.zakat),
            "neto_setelah_zakat": self._number_or_blank(neto_setelah_zakat),
            "neto_setelah_kompensasi": self._number_or_blank(neto_setelah_kompensasi),
            "ptkp": self._number_or_blank(document.ptkp),
            "pkp": self._number_or_blank(document.pkp),
            "pph_terutang": self._number_or_blank(document.pph_terutang),
            "jumlah_pph_terutang": self._number_or_blank(document.pph_terutang),
            "kredit_pajak": self._number_or_blank(document.kredit_pajak),
            "pph25": self._number_or_blank(document.pph25),
            "kurang_lebih_bayar": self._number_or_blank(pph_kurang_lebih_19),
        }

        for logical_name, value in values.items():
            acroform_name = INDUK_FIELDS.get(logical_name)
            if acroform_name:
                result.fields[acroform_name] = value

        result.fields["AUTO15"] = self._number_or_blank(jumlah_neto)
        result.fields["PPhLebihKurang"] = self._number_or_blank(pph_kurang_lebih_16)

        result.issues.append(
            IndukMappingIssue(
                "INDUK_W01",
                "WARNING",
                "Penghasilan neto usaha non-final (PNUsaha) belum memiliki sumber domain tersendiri; angka 1 dibiarkan kosong. Penghasilan UMKM final tidak dipindahkan ke angka 1.",
            )
        )
        result.issues.append(
            IndukMappingIssue(
                "INDUK_W02",
                "WARNING",
                "Kompensasi kerugian belum dimodelkan; angka 8 dibiarkan kosong dan angka 9 meneruskan nilai angka 7.",
            )
        )
        return result

    @staticmethod
    def _remove_interactive_features(writer) -> None:
        """Buang seluruh fitur interaktif setelah appearance ditanam ke halaman."""
        # Setelah flatten, widget form sudah menjadi bagian dari page content.
        # Semua annotation dibuang supaya tidak ada area klik/field tersisa.
        for page in writer.pages:
            if "/Annots" in page:
                del page["/Annots"]
            if "/AA" in page:
                del page["/AA"]

        root = writer.root_object
        for key in ("/AcroForm", "/OpenAction", "/AA"):
            if key in root:
                del root[key]

        # Names dapat membawa JavaScript pada PDF interaktif. Hapus hanya cabang
        # JavaScript bila ada; destination/bookmark lain tidak perlu disentuh.
        names = root.get("/Names")
        try:
            names_obj = names.get_object() if names is not None else None
            if names_obj is not None and "/JavaScript" in names_obj:
                del names_obj["/JavaScript"]
        except (AttributeError, TypeError):
            pass

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
        export_page_indexes = [int(page_no) - 1 for page_no in manager.INDONESIAN_EXPORT_PAGES]
        writer = PdfWriter()
        writer.append(reader, pages=export_page_indexes)

        if not writer.pages:
            raise ValueError("Template 1770 tidak menghasilkan halaman Bahasa Indonesia.")

        # flatten=True menyalin appearance field ke content stream halaman.
        # Setelah itu widget/AcroForm dapat dihapus tanpa menghilangkan nilai.
        try:
            writer.update_page_form_field_values(
                writer.pages[0],
                mapping.fields,
                auto_regenerate=False,
                flatten=True,
            )
        except TypeError as exc:
            raise RuntimeError(
                "Versi pypdf yang digunakan belum mendukung flatten Form PDF. "
                "Perbarui dengan: python -m pip install -U pypdf"
            ) from exc

        self._remove_interactive_features(writer)

        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)

        return mapping
