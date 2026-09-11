from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from core.coretax_official_schema import get_official_schema
from core.reverse_coretax_mapping import CATEGORY_ORDER


@dataclass(frozen=True)
class OfficialPackageValidationIssue:
    code: str
    severity: str
    message: str
    category: Optional[str] = None


@dataclass
class OfficialPackageValidationResult:
    package_dir: Path
    checked_files: Dict[str, Path] = field(default_factory=dict)
    issues: List[OfficialPackageValidationIssue] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)

    @property
    def errors(self) -> List[OfficialPackageValidationIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[OfficialPackageValidationIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors


class OfficialCoretaxPackageValidator:
    """Stage 8D.4F/8D.4H - validator paket resmi yang fleksibel per kategori data."""

    MANIFEST_VERSION = 1

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _error(
        result: OfficialPackageValidationResult,
        code: str,
        message: str,
        category: Optional[str] = None,
    ) -> None:
        result.issues.append(
            OfficialPackageValidationIssue(code, "ERROR", message, category)
        )

    def _load_manifest(self, result: OfficialPackageValidationResult) -> bool:
        manifest_path = result.package_dir / "manifest.json"
        if not manifest_path.is_file():
            self._error(result, "RCX4F_001", "manifest.json tidak ditemukan.")
            return False

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._error(
                result,
                "RCX4F_002",
                f"manifest.json tidak dapat dibaca: {exc}",
            )
            return False

        if not isinstance(manifest, dict):
            self._error(
                result,
                "RCX4F_003",
                "Root manifest harus berupa object JSON.",
            )
            return False

        result.manifest = manifest
        result.checked_files["MANIFEST"] = manifest_path
        return True

    def _validate_manifest_contract(
        self,
        result: OfficialPackageValidationResult,
    ) -> None:
        manifest = result.manifest

        if manifest.get("manifest_version") != self.MANIFEST_VERSION:
            self._error(
                result,
                "RCX4F_010",
                f"Versi manifest tidak didukung: {manifest.get('manifest_version')!r}.",
            )

        if manifest.get("stage") != "8D.4E":
            self._error(
                result,
                "RCX4F_011",
                f"Stage manifest tidak sesuai: {manifest.get('stage')!r}.",
            )

        for field_name in (
            "npwp",
            "tahun_pajak",
            "revision",
            "snapshot_hash",
            "total_rows",
            "excel",
            "xml",
        ):
            if field_name not in manifest:
                self._error(
                    result,
                    "RCX4F_012",
                    f"Field manifest wajib tidak ditemukan: {field_name}",
                )

    def _validate_hash(
        self,
        result: OfficialPackageValidationResult,
        path: Path,
        expected_hash: object,
        category: str,
        code_prefix: str,
    ) -> None:
        expected = str(expected_hash or "").strip().lower()
        actual = self._sha256(path).lower()
        if not expected or actual != expected:
            self._error(
                result,
                f"{code_prefix}_HASH",
                (
                    f"SHA-256 file {path.name} tidak sama dengan manifest. "
                    f"expected={expected or '-'} actual={actual}"
                ),
                category,
            )

    def _validate_excel_file(
        self,
        result: OfficialPackageValidationResult,
        category: str,
        item: dict,
    ) -> None:
        path = result.package_dir / str(item.get("path") or "")
        if not path.is_file():
            self._error(
                result,
                "RCX4F_EXCEL_MISSING",
                f"File Excel tidak ditemukan: {item.get('path') or '-'}",
                category,
            )
            return

        result.checked_files[f"EXCEL:{category}"] = path
        self._validate_hash(
            result, path, item.get("sha256"), category, "RCX4F_EXCEL"
        )

        schema = get_official_schema(category)
        try:
            wb = load_workbook(path, data_only=False, read_only=True)
        except Exception as exc:
            self._error(
                result,
                "RCX4F_EXCEL_OPEN",
                f"File Excel tidak dapat dibuka: {path.name}: {exc}",
                category,
            )
            return

        try:
            if schema.excel_sheet not in wb.sheetnames:
                self._error(
                    result,
                    "RCX4F_EXCEL_SHEET",
                    f"Sheet {schema.excel_sheet!r} tidak ditemukan pada {path.name}.",
                    category,
                )
                return

            ws = wb[schema.excel_sheet]
            actual_headers = tuple(
                str(ws.cell(3, column).value or "").strip()
                for column in range(1, len(schema.excel_headers) + 1)
            )
            expected_headers = tuple(str(v).strip() for v in schema.excel_headers)
            if actual_headers != expected_headers:
                self._error(
                    result,
                    "RCX4F_EXCEL_HEADER",
                    f"Header Excel {category} berubah dari kontrak resmi.",
                    category,
                )

            actual_rows = sum(
                1
                for row_index in range(4, ws.max_row + 1)
                if any(
                    ws.cell(row_index, column).value not in (None, "")
                    for column in range(1, len(schema.excel_headers) + 1)
                )
            )
            expected_rows = int(item.get("rows") or 0)
            if actual_rows != expected_rows:
                self._error(
                    result,
                    "RCX4F_EXCEL_ROWS",
                    (
                        f"Jumlah baris Excel {category} berbeda: "
                        f"manifest={expected_rows}, actual={actual_rows}."
                    ),
                    category,
                )
        finally:
            wb.close()

    def _validate_xml_file(
        self,
        result: OfficialPackageValidationResult,
        category: str,
        item: dict,
    ) -> None:
        path = result.package_dir / str(item.get("path") or "")
        if not path.is_file():
            self._error(
                result,
                "RCX4F_XML_MISSING",
                f"File XML tidak ditemukan: {item.get('path') or '-'}",
                category,
            )
            return

        result.checked_files[f"XML:{category}"] = path
        self._validate_hash(
            result, path, item.get("sha256"), category, "RCX4F_XML"
        )

        schema = get_official_schema(category)
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            self._error(
                result,
                "RCX4F_XML_PARSE",
                f"XML tidak dapat dibaca: {path.name}: {exc}",
                category,
            )
            return

        if root.tag != schema.xml_root:
            self._error(
                result,
                "RCX4F_XML_ROOT",
                (
                    f"Root XML {category} tidak sesuai: "
                    f"expected={schema.xml_root}, actual={root.tag}."
                ),
                category,
            )
            return

        root_children = tuple(child.tag for child in list(root))
        expected_root_children = (
            schema.xml_tin_field,
            schema.xml_year_field,
            schema.xml_list,
        )
        if root_children != expected_root_children:
            self._error(
                result,
                "RCX4F_XML_STRUCTURE",
                (
                    f"Struktur root XML {category} tidak sesuai: "
                    f"expected={expected_root_children}, actual={root_children}."
                ),
                category,
            )
            return

        expected_tin = str(result.manifest.get("npwp") or "").strip()
        actual_tin = str(root.findtext(schema.xml_tin_field) or "").strip()
        if actual_tin != expected_tin:
            self._error(
                result,
                "RCX4F_XML_TIN",
                (
                    f"TIN XML {category} berbeda dari manifest: "
                    f"expected={expected_tin}, actual={actual_tin}."
                ),
                category,
            )

        expected_year = str(result.manifest.get("tahun_pajak") or "").strip()
        actual_year = str(root.findtext(schema.xml_year_field) or "").strip()
        if actual_year != expected_year:
            self._error(
                result,
                "RCX4F_XML_YEAR",
                (
                    f"TaxPeriodYear XML {category} berbeda dari manifest: "
                    f"expected={expected_year}, actual={actual_year}."
                ),
                category,
            )

        container = root.find(schema.xml_list)
        if container is None:
            self._error(
                result,
                "RCX4F_XML_LIST",
                f"Container {schema.xml_list} tidak ditemukan.",
                category,
            )
            return

        rows = list(container.findall(schema.xml_item))
        expected_rows = int(item.get("rows") or 0)
        if len(rows) != expected_rows:
            self._error(
                result,
                "RCX4F_XML_ROWS",
                (
                    f"Jumlah item XML {category} berbeda: "
                    f"manifest={expected_rows}, actual={len(rows)}."
                ),
                category,
            )

        for row_index, row in enumerate(rows, start=1):
            if tuple(child.tag for child in list(row)) != schema.xml_fields:
                self._error(
                    result,
                    "RCX4F_XML_FIELDS",
                    (
                        f"Urutan field XML {category} baris {row_index} "
                        "berubah dari kontrak resmi."
                    ),
                    category,
                )
                break

    def _validate_file_sections(
        self,
        result: OfficialPackageValidationResult,
    ) -> None:
        manifest = result.manifest
        excel = manifest.get("excel")
        xml = manifest.get("xml")

        if not isinstance(excel, dict):
            self._error(result, "RCX4F_020", "Bagian excel pada manifest tidak valid.")
            return
        if not isinstance(xml, dict):
            self._error(result, "RCX4F_021", "Bagian xml pada manifest tidak valid.")
            return

        excel_files = excel.get("files")
        xml_files = xml.get("files")
        if not isinstance(excel_files, dict):
            self._error(result, "RCX4F_022", "excel.files pada manifest tidak valid.")
            excel_files = {}
        if not isinstance(xml_files, dict):
            self._error(result, "RCX4F_023", "xml.files pada manifest tidak valid.")
            xml_files = {}

        excel_categories = tuple(excel_files.keys())
        xml_categories = tuple(xml_files.keys())
        allowed = set(CATEGORY_ORDER)

        if not excel_categories:
            self._error(
                result,
                "RCX4H_010",
                "Manifest tidak memiliki kategori Excel berisi data.",
            )

        unknown_excel = [c for c in excel_categories if c not in allowed]
        unknown_xml = [c for c in xml_categories if c not in allowed]
        if unknown_excel:
            self._error(
                result,
                "RCX4H_011",
                f"Kategori Excel tidak dikenal: {unknown_excel}",
            )
        if unknown_xml:
            self._error(
                result,
                "RCX4H_012",
                f"Kategori XML tidak dikenal: {unknown_xml}",
            )

        expected_xml = tuple(
            category
            for category in excel_categories
            if category in allowed and get_official_schema(category).has_xml_reference
        )
        expected_unsupported = tuple(
            category
            for category in excel_categories
            if category in allowed and not get_official_schema(category).has_xml_reference
        )
        unsupported = tuple(xml.get("unsupported_categories") or ())

        if xml_categories != expected_xml:
            self._error(
                result,
                "RCX4H_013",
                (
                    "Kategori XML harus mengikuti kategori berdata yang memiliki "
                    f"referensi XML. expected={list(expected_xml)}, actual={list(xml_categories)}"
                ),
            )

        if unsupported != expected_unsupported:
            self._error(
                result,
                "RCX4H_014",
                (
                    "Kategori XML unsupported harus berasal dari kategori berdata "
                    f"tanpa schema XML. expected={list(expected_unsupported)}, "
                    f"actual={list(unsupported)}"
                ),
            )

        if int(excel.get("file_count") or 0) != len(excel_files):
            self._error(
                result,
                "RCX4F_027",
                "excel.file_count tidak sama dengan jumlah file di manifest.",
            )
        if int(xml.get("file_count") or 0) != len(xml_files):
            self._error(
                result,
                "RCX4F_028",
                "xml.file_count tidak sama dengan jumlah file di manifest.",
            )

        total_excel_rows = 0
        for category, item in excel_files.items():
            if category not in allowed or not isinstance(item, dict):
                continue
            total_excel_rows += int(item.get("rows") or 0)
            self._validate_excel_file(result, category, item)

        for category, item in xml_files.items():
            if category not in allowed or not isinstance(item, dict):
                continue
            self._validate_xml_file(result, category, item)

        manifest_total = int(manifest.get("total_rows") or 0)
        if total_excel_rows != manifest_total:
            self._error(
                result,
                "RCX4H_015",
                (
                    "Total baris kategori Excel tidak sama dengan total_rows manifest: "
                    f"excel={total_excel_rows}, manifest={manifest_total}."
                ),
            )

    def validate(self, package_dir: str | Path) -> OfficialPackageValidationResult:
        result = OfficialPackageValidationResult(package_dir=Path(package_dir))

        if not result.package_dir.is_dir():
            self._error(
                result,
                "RCX4F_000",
                f"Folder paket tidak ditemukan: {result.package_dir}",
            )
            return result

        if not self._load_manifest(result):
            return result

        self._validate_manifest_contract(result)
        self._validate_file_sections(result)

        if result.ok:
            result.issues.append(
                OfficialPackageValidationIssue(
                    "RCX4F_INFO",
                    "INFO",
                    (
                        "Paket resmi Coretax valid dan konsisten dengan kategori "
                        "Harta yang benar-benar tersedia."
                    ),
                )
            )

        return result
