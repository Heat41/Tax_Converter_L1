import re
from typing import Dict, Iterable, List, Mapping, Optional, Set

from .models import CoretaxFieldRule, ValidationIssue, ValidationResult, ValidationSeverity
from .rules import get_rules


class ValidationEngine:
    """Declarative validator for populated Coretax category rows."""

    def __init__(self, references: Optional[Mapping[str, Iterable[str]]] = None):
        self.references: Dict[str, Set[str]] = {
            key: {str(value).strip() for value in values if str(value).strip()}
            for key, values in (references or {}).items()
        }

    @staticmethod
    def _normalize(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _header_candidates(name: str) -> Set[str]:
        normalized = re.sub(r"\s+", " ", name.strip().rstrip("*"))
        return {name, normalized, normalized.lower()}

    def _find_value(self, row: Mapping[str, object], excel_name: str) -> object:
        candidates = self._header_candidates(excel_name)
        for key, value in row.items():
            key_candidates = self._header_candidates(str(key))
            if candidates & key_candidates:
                return value
        return ""

    def validate_rows(
        self,
        category: str,
        headers: List[str],
        rows: List[List[object]],
        *,
        spt_year: Optional[int] = None,
    ) -> ValidationResult:
        result = ValidationResult(total_rows=len(rows))
        rules = get_rules(category)

        if not rules:
            issue = ValidationIssue(
                None, None, "UNKNOWN_CATEGORY", ValidationSeverity.ERROR,
                f"Kategori Coretax tidak memiliki aturan validasi: {category}.", category,
            )
            result.add(issue)
            result.invalid_rows = len(rows)
            return result

        for row_number, values in enumerate(rows, start=2):
            row = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
            row_errors_before = len(result.errors)

            for rule in rules:
                value = self._find_value(row, rule.excel_name)
                self._validate_rule(result, row_number, rule, value, spt_year=spt_year)

            if len(result.errors) == row_errors_before:
                result.valid_rows += 1
            else:
                result.invalid_rows += 1

        result.is_valid = not result.errors
        return result

    def _validate_rule(
        self,
        result: ValidationResult,
        row_number: int,
        rule: CoretaxFieldRule,
        value: object,
        *,
        spt_year: Optional[int],
    ) -> None:
        text = self._normalize(value)

        if "required" in rule.validators and not text:
            result.add(ValidationIssue(
                row_number, rule.excel_name, "REQUIRED_FIELD",
                ValidationSeverity.ERROR,
                f"Kolom {rule.excel_name.rstrip('*').strip()} wajib diisi.", value,
            ))
            return

        if not text:
            return

        if "npwp16" in rule.validators and not re.fullmatch(r"\d{16}", text):
            result.add(ValidationIssue(
                row_number, rule.excel_name, "INVALID_NPWP",
                ValidationSeverity.ERROR,
                "Format NPWP harus berupa 16 digit angka.", value,
            ))

        if "digits4" in rule.validators and not re.fullmatch(r"\d{4}", text):
            result.add(ValidationIssue(
                row_number, rule.excel_name, "INVALID_YEAR",
                ValidationSeverity.ERROR,
                "Nilai harus berupa 4 digit angka.", value,
            ))

        if "positive" in rule.validators:
            try:
                numeric = float(text.replace(",", ""))
                if numeric <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                result.add(ValidationIssue(
                    row_number, rule.excel_name, "INVALID_POSITIVE_NUMBER",
                    ValidationSeverity.ERROR,
                    "Nilai harus berupa angka positif.", value,
                ))

        if rule.data_type == "year" and spt_year is not None:
            try:
                year = int(text)
                if rule.excel_name.rstrip("*").strip().lower() != "tahun pajak" and year > spt_year:
                    result.add(ValidationIssue(
                        row_number, rule.excel_name, "YEAR_EXCEEDS_SPT",
                        ValidationSeverity.ERROR,
                        f"Tahun perolehan tidak boleh melebihi tahun SPT ({spt_year}).", value,
                    ))
            except ValueError:
                pass

        if "remark" in rule.validators and not re.fullmatch(r"\d{2}", text):
            result.add(ValidationIssue(
                row_number, rule.excel_name, "INVALID_REMARK",
                ValidationSeverity.ERROR,
                "Keterangan harus berupa 2 digit kode Remark atau kosong.", value,
            ))

        if "reference" in rule.validators and rule.reference:
            allowed = self.references.get(rule.reference)
            # Empty reference set means the reference source has not been wired
            # yet; do not reject legitimate data merely because no list is loaded.
            if allowed and text not in allowed:
                result.add(ValidationIssue(
                    row_number, rule.excel_name, "INVALID_REFERENCE",
                    ValidationSeverity.ERROR,
                    "Nilai tidak ditemukan pada referensi Coretax.", value,
                ))
