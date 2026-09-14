from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from core.legacy_1770_static_pdf import Legacy1770StaticPdfService
from core.physical_reconciliation import PhysicalSourceExportReconciler
from core.reverse_coretax_mapping import CATEGORY_ORDER, ReverseCoretaxMappingService
from core.reverse_coretax_official_package import OfficialCoretaxPackageExporter
from core.reverse_coretax_official_package_validator import OfficialCoretaxPackageValidator


@dataclass(frozen=True)
class UatCheckpoint:
    code: str
    label: str
    status: str
    detail: str = ""


@dataclass
class FinalUatResult:
    npwp: str
    tahun_pajak: int
    output_dir: Path
    revision: int = 0
    snapshot_hash: str = ""
    active_categories: List[str] = field(default_factory=list)
    total_rows: int = 0
    pdf_path: Optional[Path] = None
    pdf_pages: int = 0
    coretax_dir: Optional[Path] = None
    excel_files: int = 0
    xml_files: int = 0
    reconciliation_status: str = "SKIPPED"
    checkpoints: List[UatCheckpoint] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.checkpoints) and all(
            item.status in {"PASS", "SKIPPED"}
            for item in self.checkpoints
        )

    def to_dict(self) -> dict:
        return {
            "stage": "8E.1",
            "npwp": self.npwp,
            "tahun_pajak": self.tahun_pajak,
            "revision": self.revision,
            "snapshot_hash": self.snapshot_hash,
            "active_categories": list(self.active_categories),
            "total_rows": self.total_rows,
            "status": "PASS" if self.ok else "FAIL",
            "format_lama": {
                "path": str(self.pdf_path) if self.pdf_path else "",
                "pages": self.pdf_pages,
            },
            "coretax": {
                "path": str(self.coretax_dir) if self.coretax_dir else "",
                "excel_files": self.excel_files,
                "xml_files": self.xml_files,
            },
            "reconciliation_status": self.reconciliation_status,
            "checkpoints": [asdict(item) for item in self.checkpoints],
        }


class FinalUatService:
    """Stage 8E.1 - UAT end-to-end dari snapshot FINAL sampai artifact export.

    Service ini sengaja tidak menulis export_audit_log. UAT boleh diulang tanpa
    mencampur riwayat export operasional yang dibuat dari UI.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = db_path

    @staticmethod
    def _digits(value: object) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _checkpoint(
        result: FinalUatResult,
        code: str,
        label: str,
        ok: bool,
        detail: str,
    ) -> None:
        result.checkpoints.append(
            UatCheckpoint(
                code=code,
                label=label,
                status="PASS" if ok else "FAIL",
                detail=detail,
            )
        )

    def run(
        self,
        npwp: str,
        tahun_pajak: int,
        *,
        template_dir: str | Path,
        output_dir: str | Path,
        source_dir: Optional[str | Path] = None,
    ) -> FinalUatResult:
        clean_npwp = self._digits(npwp)
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)

        result = FinalUatResult(
            npwp=clean_npwp,
            tahun_pajak=int(tahun_pajak),
            output_dir=target,
        )

        package = ReverseCoretaxMappingService(
            db_path=self.db_path
        ).build_active_final(clean_npwp, int(tahun_pajak))

        result.revision = int(package.revision or 0)
        result.snapshot_hash = str(package.snapshot_hash or "")
        result.active_categories = [
            category
            for category in CATEGORY_ORDER
            if package.rows_by_category.get(category)
        ]
        result.total_rows = package.total_rows

        mapping_detail = (
            f"Revision {result.revision}; "
            f"{result.total_rows} baris; "
            f"kategori: {', '.join(result.active_categories) or '-'}"
        )
        self._checkpoint(
            result,
            "UAT_01",
            "Snapshot FINAL dapat dibaca dan direverse-map",
            package.can_export,
            mapping_detail,
        )
        if not package.can_export:
            self._write_report(result)
            return result

        pdf_path = target / (
            f"1770_format_lama_{clean_npwp}_{int(tahun_pajak)}"
            f"_rev{result.revision}.pdf"
        )
        try:
            pdf = Legacy1770StaticPdfService().finalize_active_final(
                clean_npwp,
                int(tahun_pajak),
                pdf_path,
                db_path=self.db_path,
            )
            pdf_ok = pdf.ok
            result.pdf_path = pdf.output_path
            result.pdf_pages = pdf.page_count
            pdf_detail = (
                f"{pdf.page_count} halaman; {pdf.size_bytes:,} byte; "
                f"static={'YA' if pdf.is_static else 'TIDAK'}"
            )
            if pdf.errors:
                pdf_detail += " | " + " | ".join(
                    f"{issue.code}: {issue.message}"
                    for issue in pdf.errors
                )
        except Exception as exc:
            pdf_ok = False
            pdf_detail = str(exc)

        self._checkpoint(
            result,
            "UAT_02",
            "Format Lama PDF statis berhasil dibuat",
            pdf_ok,
            pdf_detail,
        )

        coretax_dir = target / "coretax_package"
        result.coretax_dir = coretax_dir
        try:
            export_result = OfficialCoretaxPackageExporter(
                template_dir
            ).export_package(package, coretax_dir)
            export_ok = export_result.ok
            if export_result.excel_result is not None:
                result.excel_files = len(export_result.excel_result.files)
            if export_result.xml_result is not None:
                result.xml_files = len(export_result.xml_result.files)
            export_detail = (
                f"{result.excel_files} Excel + {result.xml_files} XML"
            )
            if export_result.errors:
                export_detail += " | " + " | ".join(
                    f"{issue.code}: {issue.message}"
                    for issue in export_result.errors
                )
        except Exception as exc:
            export_ok = False
            export_detail = str(exc)

        self._checkpoint(
            result,
            "UAT_03",
            "Paket Coretax berhasil dibuat",
            export_ok,
            export_detail,
        )

        if export_ok:
            validation = OfficialCoretaxPackageValidator().validate(
                coretax_dir
            )
            validation_ok = validation.ok
            validation_detail = (
                f"{len(validation.checked_files)} artifact diperiksa"
            )
            if validation.errors:
                validation_detail += " | " + " | ".join(
                    f"{issue.code}: {issue.message}"
                    for issue in validation.errors
                )
        else:
            validation_ok = False
            validation_detail = "Dilewati karena export Paket Coretax gagal."

        self._checkpoint(
            result,
            "UAT_04",
            "Validator Paket Coretax PASS",
            validation_ok,
            validation_detail,
        )

        if source_dir:
            if export_ok:
                reconciliation = PhysicalSourceExportReconciler().reconcile(
                    source_dir,
                    coretax_dir,
                )
                reconciliation_ok = reconciliation.ok
                result.reconciliation_status = (
                    "PASS" if reconciliation_ok else "FAIL"
                )
                detail = (
                    f"{len(reconciliation.categories)} kategori dibandingkan"
                )
                if reconciliation.errors:
                    detail += " | " + " | ".join(
                        (
                            f"{issue.code}"
                            + (f"[{issue.category}]" if issue.category else "")
                            + f": {issue.message}"
                        )
                        for issue in reconciliation.errors
                    )
                self._checkpoint(
                    result,
                    "UAT_05",
                    "Rekonsiliasi fisik source vs export",
                    reconciliation_ok,
                    detail,
                )
            else:
                result.reconciliation_status = "FAIL"
                self._checkpoint(
                    result,
                    "UAT_05",
                    "Rekonsiliasi fisik source vs export",
                    False,
                    "Tidak dapat dijalankan karena export Paket Coretax gagal.",
                )
        else:
            result.reconciliation_status = "SKIPPED"
            result.checkpoints.append(
                UatCheckpoint(
                    code="UAT_05",
                    label="Rekonsiliasi fisik source vs export",
                    status="SKIPPED",
                    detail="Folder sumber tidak diberikan.",
                )
            )

        self._write_report(result)
        return result

    @staticmethod
    def _write_report(result: FinalUatResult) -> Path:
        path = result.output_dir / "uat_report.json"
        path.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
