from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from core.legacy_1770 import Legacy1770Document, Legacy1770DocumentService
from core.legacy_1770_multipage_final import Legacy1770MultipageService
from core.legacy_pdf_template import DEFAULT_TEMPLATE_PATH


@dataclass(frozen=True)
class StaticPdfIssue:
    code: str
    severity: str
    message: str


@dataclass
class StaticPdfResult:
    output_path: Path
    page_count: int = 0
    size_bytes: int = 0
    sha256: str = ""
    is_static: bool = False
    issues: List[StaticPdfIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[StaticPdfIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[StaticPdfIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors and self.is_static and self.page_count > 0


class Legacy1770StaticPdfService:
    """Stage 8C.10 - final static PDF untuk Form 1770 lama.

    Tahap ini TIDAK merasterisasi, memperkecil, atau mengubah skala halaman.
    Seluruh vector content dan ukuran font yang sudah dikalibrasi pada Stage
    8C.4-8C.9 dipertahankan persis. Pekerjaan di sini hanya:
    - membentuk output multipage final,
    - menghapus elemen interaktif/annotation/action,
    - menulis ulang PDF statis,
    - memverifikasi hasil akhir.
    """

    ROOT_INTERACTIVE_KEYS = (
        "/AcroForm",
        "/OpenAction",
        "/AA",
    )
    PAGE_INTERACTIVE_KEYS = (
        "/Annots",
        "/AA",
    )

    @staticmethod
    def _remove_root_interactivity(writer) -> None:
        root = writer._root_object
        for key in Legacy1770StaticPdfService.ROOT_INTERACTIVE_KEYS:
            if key in root:
                del root[key]

        # JavaScript, embedded files, dan name-tree interaktif tidak diperlukan
        # pada arsip Form 1770 statis. Menghapus /Names tidak memengaruhi isi
        # visual halaman yang sudah menjadi page content.
        if "/Names" in root:
            del root["/Names"]

    @staticmethod
    def _remove_page_interactivity(page) -> None:
        for key in Legacy1770StaticPdfService.PAGE_INTERACTIVE_KEYS:
            if key in page:
                del page[key]

    @classmethod
    def _write_static_copy(cls, source: Path, target: Path) -> None:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf diperlukan untuk Stage 8C.10."
            ) from exc

        reader = PdfReader(str(source))
        writer = PdfWriter()

        # add_page mempertahankan ukuran media box dan content stream asli,
        # sehingga font/posisi hasil kalibrasi tidak berubah.
        for source_page in reader.pages:
            cls._remove_page_interactivity(source_page)
            writer.add_page(source_page)

        cls._remove_root_interactivity(writer)

        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            writer.write(handle)

    @classmethod
    def inspect_static_pdf(cls, path: str | Path) -> StaticPdfResult:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf diperlukan untuk memverifikasi Stage 8C.10."
            ) from exc

        target = Path(path)
        result = StaticPdfResult(output_path=target)

        if not target.is_file():
            result.issues.append(
                StaticPdfIssue("S10_001", "ERROR", "File PDF final tidak ditemukan.")
            )
            return result

        data = target.read_bytes()
        result.size_bytes = len(data)
        result.sha256 = hashlib.sha256(data).hexdigest()

        try:
            reader = PdfReader(str(target))
        except Exception as exc:
            result.issues.append(
                StaticPdfIssue(
                    "S10_002",
                    "ERROR",
                    f"PDF final tidak dapat dibaca: {exc}",
                )
            )
            return result

        result.page_count = len(reader.pages)
        root = reader.trailer.get("/Root", {})

        root_hits = [
            key for key in cls.ROOT_INTERACTIVE_KEYS
            if key in root
        ]
        if "/Names" in root:
            root_hits.append("/Names")

        page_hits = []
        for index, page in enumerate(reader.pages, start=1):
            hits = [key for key in cls.PAGE_INTERACTIVE_KEYS if key in page]
            if hits:
                page_hits.append((index, hits))

        if root_hits:
            result.issues.append(
                StaticPdfIssue(
                    "S10_003",
                    "ERROR",
                    "Catalog PDF masih memuat elemen interaktif: "
                    + ", ".join(root_hits),
                )
            )

        if page_hits:
            detail = "; ".join(
                f"halaman {page_no}: {', '.join(keys)}"
                for page_no, keys in page_hits
            )
            result.issues.append(
                StaticPdfIssue(
                    "S10_004",
                    "ERROR",
                    "Halaman PDF masih memuat annotation/action: " + detail,
                )
            )

        if result.size_bytes <= 0:
            result.issues.append(
                StaticPdfIssue("S10_005", "ERROR", "Ukuran file PDF final kosong.")
            )

        result.is_static = not result.errors
        return result

    def finalize_document(
        self,
        document: Legacy1770Document,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
    ) -> StaticPdfResult:
        target = Path(output_path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        if not document.can_export_pdf:
            result = StaticPdfResult(output_path=target)
            result.issues.append(
                StaticPdfIssue(
                    "S10_006",
                    "ERROR",
                    "Snapshot FINAL belum siap untuk ekspor PDF.",
                )
            )
            return result

        with TemporaryDirectory(prefix="tax1770_static_") as temp_dir:
            intermediate = Path(temp_dir) / "1770_multipage_intermediate.pdf"
            multipage = Legacy1770MultipageService()
            plan = multipage.fill_multipage(
                document,
                intermediate,
                template_path=template_path or DEFAULT_TEMPLATE_PATH,
            )

            plan_errors = [
                issue for issue in plan.issues
                if getattr(issue, "severity", "") == "ERROR"
            ]
            if plan_errors:
                result = StaticPdfResult(output_path=target)
                for issue in plan_errors:
                    result.issues.append(
                        StaticPdfIssue(
                            getattr(issue, "code", "S10_MP"),
                            "ERROR",
                            getattr(issue, "message", "Ekspor multipage gagal."),
                        )
                    )
                return result

            self._write_static_copy(intermediate, target)

        result = self.inspect_static_pdf(target)
        if result.page_count != plan.output_pages:
            result.issues.append(
                StaticPdfIssue(
                    "S10_007",
                    "ERROR",
                    f"Jumlah halaman final {result.page_count} tidak sama dengan "
                    f"rencana multipage {plan.output_pages}.",
                )
            )
            result.is_static = False

        return result

    def finalize_active_final(
        self,
        npwp: str,
        tahun_pajak: int,
        output_path: str | Path,
        *,
        template_path: Optional[str | Path] = None,
        db_path: Optional[str | Path] = None,
    ) -> StaticPdfResult:
        clean_npwp = "".join(ch for ch in str(npwp or "") if ch.isdigit())
        document = Legacy1770DocumentService(
            db_path=db_path
        ).build_active_final(
            clean_npwp,
            int(tahun_pajak),
        )
        return self.finalize_document(
            document,
            output_path,
            template_path=template_path,
        )
