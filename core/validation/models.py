from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class CoretaxFieldRule:
    category: str
    excel_name: str
    xml_name: str
    required: bool = False
    data_type: str = "text"
    validators: List[str] = field(default_factory=list)
    reference: Optional[str] = None
    raw_validation: str = ""


@dataclass(frozen=True)
class ValidationIssue:
    row: Optional[int]
    column: Optional[str]
    code: str
    severity: ValidationSeverity
    message: str
    value: Any = ""

    @property
    def is_error(self) -> bool:
        return self.severity == ValidationSeverity.ERROR


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0

    def add(self, issue: ValidationIssue) -> None:
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        else:
            self.warnings.append(issue)


@dataclass
class FileCategoryResult:
    category: str
    file_path: Optional[Path] = None
    status: str = "MISSING"
    message: str = ""
    read_result: Any = None
    validation: Optional[ValidationResult] = None
    is_template: bool = False
    is_nihil: bool = False


@dataclass
class BatchImportResult:
    selected_files: List[Path] = field(default_factory=list)
    category_files: Dict[str, Path] = field(default_factory=dict)
    category_results: Dict[str, FileCategoryResult] = field(default_factory=dict)
    missing_categories: List[str] = field(default_factory=list)
    duplicate_categories: Dict[str, List[Path]] = field(default_factory=dict)
    unknown_files: List[Path] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0

    @property
    def found_count(self) -> int:
        return len(self.category_files)

    @property
    def category_count(self) -> int:
        return 6

    @property
    def is_valid(self) -> bool:
        return not self.errors and all(
            result.validation is None or result.validation.is_valid
            for result in self.category_results.values()
        )
