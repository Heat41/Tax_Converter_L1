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

    Hanya field yang sudah didukung data Worksheet yang diisi. Field yang belum
    memiliki sumber domain tidak ditebak; kondisi tersebut dilaporkan sebagai
    warning agar hasil dapat dikoreksi sebelum Stage 8C dinyatakan selesai.
    """

    INDONESIAN_INDUK_PAGE_INDEX = 9  # halaman 10 bila dihitung dari 1

    @staticmethod
    def _number(value: object) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        if abs(number - round(number)) < 0.000001:
            return str(int(round(number)))
        return (f"{number:.2f}").rstrip("0").rstrip(".")

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

        values = {
            "npwp": document.npwp,
            "nama_wp": document.nama_wp,
            "tahun_pajak": str(document.tahun_pajak),
            # Untuk data pekerjaan, sumber yang tersedia adalah total NETTO Bupot.
            "penghasilan_pekerjaan": self._number(document.total_netto_bupot),
            "penghasilan_lainnya": self._number(document.penghasilan_neto_lainnya),
            "zakat": self._number(document.zakat),
            "neto_setelah_zakat": self._number(document.penghasilan_neto_gabungan),
            "ptkp": self._number(document.ptkp),
            "pkp": self._number(document.pkp),
            "pph_terutang": self._number(document.pph_terutang),
            "jumlah_pph_terutang": self._number(document.pph_terutang),
            "kredit_pajak": self._number(document.kredit_pajak),
            "pph25": self._number(document.pph25),
            "kurang_lebih_bayar": self._number(document.kurang_lebih_bayar),
        }

        for logical_name, value in values.items():
            acroform_name = INDUK_FIELDS.get(logical_name)
            if acroform_name:
                result.fields[acroform_name] = value

        # Belum ada sumber yang sah untuk neto usaha dan kompensasi kerugian.
        # Jangan menganggap kosong = nol secara diam-diam.
        result.issues.append(
            IndukMappingIssue(
                "INDUK_W01",
                "WARNING",
                "Penghasilan neto usaha (PNUsaha) belum memiliki sumber domain tersendiri; field dibiarkan kosong.",
            )
        )
        result.issues.append(
            IndukMappingIssue(
                "INDUK_W02",
                "WARNING",
                "Kompensasi kerugian belum dimodelkan; PNsetelahKompen tidak diisi otomatis.",
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
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)

        if len(writer.pages) <= self.INDONESIAN_INDUK_PAGE_INDEX:
            raise ValueError("Template 1770 tidak memiliki halaman Induk Bahasa Indonesia.")

        writer.update_page_form_field_values(
            writer.pages[self.INDONESIAN_INDUK_PAGE_INDEX],
            mapping.fields,
            auto_regenerate=True,
        )

        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)

        return mapping
