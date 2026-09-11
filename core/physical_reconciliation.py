from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from core.coretax_official_schema import get_official_schema
from core.reverse_coretax_mapping import CATEGORY_ORDER


@dataclass(frozen=True)
class PhysicalReconciliationIssue:
    code: str
    severity: str
    message: str
    category: Optional[str] = None
    row_number: Optional[int] = None
    field_name: Optional[str] = None


@dataclass
class CategoryReconciliation:
    category: str
    source_excel: Optional[Path] = None
    exported_excel: Optional[Path] = None
    source_xml: Optional[Path] = None
    exported_xml: Optional[Path] = None
    source_excel_rows: int = 0
    exported_excel_rows: int = 0
    source_xml_rows: int = 0
    exported_xml_rows: int = 0
    excel_match: Optional[bool] = None
    xml_match: Optional[bool] = None


@dataclass
class PhysicalReconciliationResult:
    source_dir: Path
    export_dir: Path
    categories: Dict[str, CategoryReconciliation] = field(default_factory=dict)
    issues: List[PhysicalReconciliationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[PhysicalReconciliationIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[PhysicalReconciliationIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.categories)


class PhysicalSourceExportReconciler:
    """Stage 8D.4K - rekonsiliasi file sumber Coretax vs hasil reverse-export.

    Perbandingan dilakukan terhadap kontrak Excel/XML resmi yang sudah dikunci.
    Tidak ada toleransi yang mengubah makna data; normalisasi hanya menyamakan
    representasi teknis seperti 1000 dan 1000.0 serta whitespace string.
    """

    @staticmethod
    def _normalize_filename(value: str) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    @staticmethod
    def _normalize_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float, Decimal)):
            try:
                number = Decimal(str(value))
                normalized = format(number.normalize(), "f")
                if "." in normalized:
                    normalized = normalized.rstrip("0").rstrip(".")
                return normalized or "0"
            except (InvalidOperation, ValueError):
                pass

        text = str(value).strip()
        if not text:
            return ""

        # Excel/XML kadang merepresentasikan angka sebagai string.
        numeric = text.replace(",", "")
        try:
            number = Decimal(numeric)
            normalized = format(number.normalize(), "f")
            if "." in normalized:
                normalized = normalized.rstrip("0").rstrip(".")
            return normalized or "0"
        except InvalidOperation:
            return " ".join(text.split())

    @classmethod
    def _find_excel(cls, directory: Path, category: str) -> Optional[Path]:
        schema = get_official_schema(category)
        hint = cls._normalize_filename(schema.excel_filename_hint)
        candidates: List[Path] = []
        for path in directory.rglob("*.xlsx"):
            if hint in cls._normalize_filename(path.stem):
                candidates.append(path)
        if not candidates:
            return None
        candidates.sort(
            key=lambda path: (
                abs(len(cls._normalize_filename(path.stem)) - len(hint)),
                str(path).lower(),
            )
        )
        return candidates[0]

    @staticmethod
    def _find_xml(directory: Path, category: str) -> Optional[Path]:
        schema = get_official_schema(category)
        if not schema.has_xml_reference:
            return None

        candidates: List[Path] = []
        for path in directory.rglob("*.xml"):
            try:
                root = ET.parse(path).getroot()
            except (OSError, ET.ParseError):
                continue
            if root.tag == schema.xml_root:
                candidates.append(path)

        if not candidates:
            return None
        candidates.sort(key=lambda path: str(path).lower())
        return candidates[0]

    @staticmethod
    def _resolve_excel_value(ws, value: object) -> object:
        if not isinstance(value, str):
            return value
        formula = value.strip()
        match = re.fullmatch(r"=\$?([A-Z]+)\$?(\d+)", formula)
        if not match:
            return value
        return ws[f"{match.group(1)}{match.group(2)}"].value

    @classmethod
    def _read_excel(
        cls,
        path: Path,
        category: str,
    ) -> Tuple[Tuple[str, ...], List[Tuple[str, ...]]]:
        schema = get_official_schema(category)
        wb = load_workbook(path, data_only=False, read_only=False)
        try:
            if schema.excel_sheet not in wb.sheetnames:
                raise ValueError(
                    f"Sheet {schema.excel_sheet} tidak ditemukan pada {path.name}."
                )
            ws = wb[schema.excel_sheet]
            headers = tuple(
                str(ws.cell(3, col).value or "").strip()
                for col in range(1, len(schema.excel_headers) + 1)
            )
            rows: List[Tuple[str, ...]] = []
            for row_index in range(4, ws.max_row + 1):
                raw = tuple(
                    cls._resolve_excel_value(
                        ws,
                        ws.cell(row_index, col).value,
                    )
                    for col in range(1, len(schema.excel_headers) + 1)
                )
                if not any(value not in (None, "") for value in raw):
                    continue
                rows.append(tuple(cls._normalize_value(value) for value in raw))
            return headers, rows
        finally:
            wb.close()

    @classmethod
    def _read_xml(
        cls,
        path: Path,
        category: str,
    ) -> List[Tuple[str, ...]]:
        schema = get_official_schema(category)
        root = ET.parse(path).getroot()
        if root.tag != schema.xml_root:
            raise ValueError(
                f"Root XML {path.name} adalah {root.tag}, expected {schema.xml_root}."
            )

        rows: List[Tuple[str, ...]] = []
        for item in root.findall(schema.xml_list):
            rows.append(
                tuple(
                    cls._normalize_value(item.findtext(field_name))
                    for field_name in schema.xml_fields
                )
            )
        return rows

    @staticmethod
    def _compare_rows(
        result: PhysicalReconciliationResult,
        category: str,
        source_rows: Sequence[Tuple[str, ...]],
        exported_rows: Sequence[Tuple[str, ...]],
        field_names: Sequence[str],
        kind: str,
    ) -> bool:
        matched = True

        if len(source_rows) != len(exported_rows):
            matched = False
            result.issues.append(
                PhysicalReconciliationIssue(
                    f"RCX4K_{kind}_ROWS",
                    "ERROR",
                    (
                        f"Jumlah baris {kind} berbeda: "
                        f"source={len(source_rows)}, export={len(exported_rows)}."
                    ),
                    category,
                )
            )

        limit = min(len(source_rows), len(exported_rows))
        for index in range(limit):
            source_row = source_rows[index]
            export_row = exported_rows[index]
            for field_index, field_name in enumerate(field_names):
                source_value = (
                    source_row[field_index]
                    if field_index < len(source_row)
                    else ""
                )
                export_value = (
                    export_row[field_index]
                    if field_index < len(export_row)
                    else ""
                )
                if source_value == export_value:
                    continue
                matched = False
                result.issues.append(
                    PhysicalReconciliationIssue(
                        f"RCX4K_{kind}_VALUE",
                        "ERROR",
                        (
                            f"{kind} berbeda: source={source_value!r}, "
                            f"export={export_value!r}."
                        ),
                        category,
                        index + 1,
                        field_name,
                    )
                )
        return matched

    def reconcile(
        self,
        source_dir: str | Path,
        export_dir: str | Path,
    ) -> PhysicalReconciliationResult:
        source = Path(source_dir)
        exported = Path(export_dir)
        result = PhysicalReconciliationResult(
            source_dir=source,
            export_dir=exported,
        )

        if not source.is_dir():
            result.issues.append(
                PhysicalReconciliationIssue(
                    "RCX4K_001",
                    "ERROR",
                    f"Folder sumber tidak ditemukan: {source}",
                )
            )
            return result

        if not exported.is_dir():
            result.issues.append(
                PhysicalReconciliationIssue(
                    "RCX4K_002",
                    "ERROR",
                    f"Folder hasil export tidak ditemukan: {exported}",
                )
            )
            return result

        for category in CATEGORY_ORDER:
            source_excel = self._find_excel(source, category)
            exported_excel = self._find_excel(exported, category)

            # Kategori tidak aktif tidak perlu muncul di kedua sisi.
            if source_excel is None and exported_excel is None:
                continue

            detail = CategoryReconciliation(
                category=category,
                source_excel=source_excel,
                exported_excel=exported_excel,
            )
            result.categories[category] = detail

            if source_excel is None:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_010",
                        "ERROR",
                        "Kategori ada di hasil export tetapi file Excel sumber tidak ada.",
                        category,
                    )
                )
                continue

            if exported_excel is None:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_011",
                        "ERROR",
                        "Kategori ada di sumber tetapi file Excel hasil export tidak ada.",
                        category,
                    )
                )
                continue

            schema = get_official_schema(category)
            try:
                source_headers, source_rows = self._read_excel(
                    source_excel, category
                )
                export_headers, export_rows = self._read_excel(
                    exported_excel, category
                )
            except Exception as exc:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_012",
                        "ERROR",
                        f"Excel tidak dapat direkonsiliasi: {exc}",
                        category,
                    )
                )
                continue

            detail.source_excel_rows = len(source_rows)
            detail.exported_excel_rows = len(export_rows)

            if source_headers != tuple(schema.excel_headers):
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_013",
                        "ERROR",
                        "Header Excel sumber berbeda dari kontrak resmi.",
                        category,
                    )
                )
            if export_headers != tuple(schema.excel_headers):
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_014",
                        "ERROR",
                        "Header Excel hasil export berbeda dari kontrak resmi.",
                        category,
                    )
                )

            detail.excel_match = self._compare_rows(
                result,
                category,
                source_rows,
                export_rows,
                schema.excel_headers,
                "EXCEL",
            )

            if not schema.has_xml_reference:
                continue

            detail.source_xml = self._find_xml(source, category)
            detail.exported_xml = self._find_xml(exported, category)

            if detail.source_xml is None:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_020",
                        "WARNING",
                        "XML sumber tidak ditemukan; rekonsiliasi XML dilewati.",
                        category,
                    )
                )
                continue

            if detail.exported_xml is None:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_021",
                        "ERROR",
                        "XML sumber ada tetapi XML hasil export tidak ditemukan.",
                        category,
                    )
                )
                continue

            try:
                source_xml_rows = self._read_xml(
                    detail.source_xml, category
                )
                export_xml_rows = self._read_xml(
                    detail.exported_xml, category
                )
            except Exception as exc:
                result.issues.append(
                    PhysicalReconciliationIssue(
                        "RCX4K_022",
                        "ERROR",
                        f"XML tidak dapat direkonsiliasi: {exc}",
                        category,
                    )
                )
                continue

            detail.source_xml_rows = len(source_xml_rows)
            detail.exported_xml_rows = len(export_xml_rows)
            detail.xml_match = self._compare_rows(
                result,
                category,
                source_xml_rows,
                export_xml_rows,
                schema.xml_fields,
                "XML",
            )

        if result.ok:
            result.issues.append(
                PhysicalReconciliationIssue(
                    "RCX4K_INFO",
                    "INFO",
                    (
                        "Isi fisik source dan reverse-export konsisten untuk "
                        "seluruh kategori yang tersedia."
                    ),
                )
            )

        return result
