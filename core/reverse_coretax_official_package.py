from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.reverse_coretax_mapping import (
    ReverseCoretaxMappingService,
    ReverseCoretaxPackage,
)
from core.reverse_coretax_official_excel import (
    OfficialCoretaxExcelExporter,
    OfficialExcelExportIssue,
    OfficialExcelExportResult,
)
from core.reverse_coretax_official_xml import (
    OfficialCoretaxXmlExporter,
    OfficialXmlExportIssue,
    OfficialXmlExportResult,
)


@dataclass(frozen=True)
class OfficialPackageIssue:
    code: str
    severity: str
    message: str
    category: Optional[str] = None


@dataclass
class OfficialCoretaxPackageResult:
    output_dir: Path
    excel_result: Optional[OfficialExcelExportResult] = None
    xml_result: Optional[OfficialXmlExportResult] = None
    manifest_path: Optional[Path] = None
    issues: List[OfficialPackageIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[OfficialPackageIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def ok(self) -> bool:
        return (
            not self.errors
            and self.excel_result is not None
            and self.excel_result.ok
            and self.xml_result is not None
            and self.xml_result.ok
            and self.manifest_path is not None
            and self.manifest_path.is_file()
        )


class OfficialCoretaxPackageExporter:
    """Stage 8D.4E - paket resmi Coretax dari snapshot FINAL.

    Output:
      <output>/
        excel/   -> Excel hanya untuk kategori yang memiliki data
        xml/     -> XML hanya untuk kategori berdata yang punya referensi resmi
        manifest.json
    """

    MANIFEST_VERSION = 1

    def __init__(self, template_dir: str | Path):
        self.template_dir = Path(template_dir)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _convert_issue(issue: object) -> OfficialPackageIssue:
        return OfficialPackageIssue(
            code=str(getattr(issue, "code", "")),
            severity=str(getattr(issue, "severity", "")),
            message=str(getattr(issue, "message", "")),
            category=getattr(issue, "category", None),
        )

    def _build_manifest(
        self,
        package: ReverseCoretaxPackage,
        result: OfficialCoretaxPackageResult,
    ) -> dict:
        assert result.excel_result is not None
        assert result.xml_result is not None

        excel_files: Dict[str, dict] = {}
        for category, path in result.excel_result.files.items():
            excel_files[category] = {
                "path": str(path.relative_to(result.output_dir)),
                "filename": path.name,
                "rows": result.excel_result.row_counts.get(category, 0),
                "sha256": self._sha256(path),
            }

        xml_files: Dict[str, dict] = {}
        for category, path in result.xml_result.files.items():
            xml_files[category] = {
                "path": str(path.relative_to(result.output_dir)),
                "filename": path.name,
                "rows": result.xml_result.row_counts.get(category, 0),
                "sha256": self._sha256(path),
            }

        return {
            "manifest_version": self.MANIFEST_VERSION,
            "stage": "8D.4E",
            "npwp": package.npwp,
            "nama_wp": package.nama_wp,
            "tahun_pajak": package.tahun_pajak,
            "revision": package.revision,
            "snapshot_hash": package.snapshot_hash,
            "total_rows": package.total_rows,
            "active_categories": [
                category
                for category, rows in package.rows_by_category.items()
                if rows
            ],
            "excel": {
                "file_count": len(excel_files),
                "files": excel_files,
            },
            "xml": {
                "file_count": len(xml_files),
                "files": xml_files,
                "unsupported_categories": list(
                    result.xml_result.unsupported_categories
                ),
            },
        }

    def export_package(
        self,
        package: ReverseCoretaxPackage,
        output_dir: str | Path,
    ) -> OfficialCoretaxPackageResult:
        target_dir = Path(output_dir)
        result = OfficialCoretaxPackageResult(output_dir=target_dir)

        if not package.can_export:
            result.issues.append(
                OfficialPackageIssue(
                    "RCX4E_001",
                    "ERROR",
                    "Paket snapshot FINAL belum valid untuk export resmi Coretax.",
                )
            )
            return result

        excel_dir = target_dir / "excel"
        xml_dir = target_dir / "xml"

        excel_result = OfficialCoretaxExcelExporter(
            self.template_dir
        ).export_package(
            package,
            excel_dir,
        )
        result.excel_result = excel_result
        result.issues.extend(
            self._convert_issue(issue)
            for issue in excel_result.issues
            if issue.severity in {"ERROR", "WARNING"}
        )

        if not excel_result.ok:
            result.issues.append(
                OfficialPackageIssue(
                    "RCX4E_101",
                    "ERROR",
                    "Paket resmi dihentikan karena export Excel kategori berdata belum valid.",
                )
            )
            return result

        xml_result = OfficialCoretaxXmlExporter().export_package(
            package,
            xml_dir,
        )
        result.xml_result = xml_result
        result.issues.extend(
            self._convert_issue(issue)
            for issue in xml_result.issues
            if issue.severity in {"ERROR", "WARNING"}
        )

        if not xml_result.ok:
            result.issues.append(
                OfficialPackageIssue(
                    "RCX4E_102",
                    "ERROR",
                    "Paket resmi dihentikan karena export XML belum valid.",
                )
            )
            return result

        manifest = self._build_manifest(package, result)
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = target_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result.manifest_path = manifest_path

        return result

    def export_active_final(
        self,
        npwp: str,
        tahun_pajak: int,
        output_dir: str | Path,
        *,
        db_path: Optional[str | Path] = None,
    ) -> OfficialCoretaxPackageResult:
        package = ReverseCoretaxMappingService(
            db_path=db_path
        ).build_active_final(
            npwp,
            tahun_pajak,
        )

        result = self.export_package(package, output_dir)

        for issue in package.issues:
            if issue.severity in {"ERROR", "WARNING"}:
                result.issues.append(
                    OfficialPackageIssue(
                        issue.code,
                        issue.severity,
                        issue.message,
                    )
                )

        return result
