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
    """Stage 8C.4 - mapping snapshot FINAL ke AcroForm Induk 1770 Indonesia.

    Nilai mengikuti arti baris Form 1770 lama. File Lisa hanya menjadi acuan
    visual/struktur; seluruh data yang ditulis tetap berasal dari snapshot FINAL
    WP aktif dan tidak pernah mengambil identitas atau angka milik Lisa.

    Output PDF hanya lima halaman Bahasa Indonesia: Induk, Lampiran I halaman 2,
    Lampiran II, Lampiran III, dan Lampiran IV.
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

        # Urutan angka pada Induk 1770 lama:
        # 1 usaha/pekerjaan bebas, 2 pekerjaan, 3 DN lainnya, 4 LN,
        # 5 jumlah neto, 6 zakat, 7 neto setelah zakat, 8 kompensasi,
        # 9 neto setelah kompensasi, 10 PTKP, 11 PKP, dst.
        pekerjaan = float(document.total_netto_bupot or 0)
        lainnya = float(document.penghasilan_neto_lainnya or 0)
        jumlah_neto = pekerjaan + lainnya
        neto_setelah_zakat = jumlah_neto - float(document.zakat or 0)

        # Kompensasi kerugian belum memiliki modul tersendiri. Baris 8 dibiarkan
        # kosong; untuk menjaga kesinambungan form, angka 9 meneruskan angka 7.
        neto_setelah_kompensasi = neto_setelah_zakat

        # Angka 16 = angka 14 - angka 15. Angka 19 = angka 16 - angka 18.
        # Saat ini Worksheet hanya memiliki PPh25 sebagai kredit yang dibayar sendiri.
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

        # AUTO15 adalah angka 5 pada template resmi. Diisi eksplisit agar hasil
        # tetap benar pada PDF viewer yang tidak menjalankan kalkulasi JavaScript.
        result.fields["AUTO15"] = self._number_or_blank(jumlah_neto)

        # PPhLebihKurang adalah angka 16 pada template resmi.
        result.fields["PPhLebihKurang"] = self._number_or_blank(pph_kurang_lebih_16)

        # PNUsaha tidak boleh diambil dari omzet UMKM karena UMKM dikenai PPh Final
        # dan akan ditempatkan pada Lampiran III.
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
                "Library pypdf diperlukan untuk mengisi Form 1770. Install dengan: python -m pip install pypdf"
            ) from exc

        reader = PdfReader(str(info.path))
        filled_writer = PdfWriter()
        filled_writer.clone_document_from_reader(reader)

        if len(filled_writer.pages) <= self.INDONESIAN_INDUK_PAGE_INDEX:
            raise ValueError("Template 1770 tidak memiliki halaman Induk Bahasa Indonesia.")

        filled_writer.update_page_form_field_values(
            filled_writer.pages[self.INDONESIAN_INDUK_PAGE_INDEX],
            mapping.fields,
            auto_regenerate=True,
        )

        output_writer = PdfWriter()
        for page_number in manager.INDONESIAN_EXPORT_PAGES:
            source_index = int(page_number) - 1
            if source_index < 0 or source_index >= len(filled_writer.pages):
                raise ValueError(
                    f"Template 1770 tidak memiliki halaman Bahasa Indonesia {page_number}."
                )
            output_writer.add_page(filled_writer.pages[source_index])

        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            output_writer.write(handle)

        return mapping
