from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from core.reverse_coretax_excel import ReverseCoretaxExcelExporter
from core.reverse_coretax_mapping import (
    CATEGORY_ORDER,
    ReverseCoretaxMappingService,
    ReverseCoretaxPackage,
)


@dataclass(frozen=True)
class ReverseCoretaxRoundtripIssue:
    code: str
    severity: str
    category: str
    message: str
    row_number: Optional[int] = None


@dataclass
class ReverseCoretaxRoundtripResult:
    output_dir: Path
    checked_files: Dict[str, Path] = field(default_factory=dict)
    expected_counts: Dict[str, int] = field(default_factory=dict)
    actual_counts: Dict[str, int] = field(default_factory=dict)
    issues: List[ReverseCoretaxRoundtripIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ReverseCoretaxRoundtripIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[ReverseCoretaxRoundtripIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors and len(self.checked_files) == 6


class ReverseCoretaxRoundtripValidator:
    """Stage 8D.3 - validasi round-trip kontrak 6 file Excel.

    File hasil 8D.2 dibaca ulang dari disk, dinormalisasi menggunakan kontrak
    kolom yang sama dengan importer internal, lalu dibandingkan dengan paket
    snapshot FINAL. Validator tidak menulis ke database sehingga aman untuk
    pengujian tanpa menghapus/mengganti data Harta yang sedang aktif.
    """

    FLOAT_TOLERANCE = 0.5

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
        return str(value).strip()

    @staticmethod
    def _number(value: object) -> float:
        if value is None:
            return 0.0
        try:
            if pd.isna(value):
                return 0.0
        except Exception:
            pass
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("Rp", "").replace(" ", "")
        if not text:
            return 0.0
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        return float(text)

    @staticmethod
    def _expected_rows(
        package: ReverseCoretaxPackage,
        category: str,
    ) -> List[Tuple[object, ...]]:
        return [
            tuple(ReverseCoretaxExcelExporter._row_values(row))
            for row in package.rows_by_category.get(category, [])
        ]

    @classmethod
    def _compare_cell(
        cls,
        expected: object,
        actual: object,
        header: str,
    ) -> bool:
        if header in {"tahun_perolehan", "harga_perolehan"}:
            return abs(cls._number(expected) - cls._number(actual)) <= cls.FLOAT_TOLERANCE
        return cls._text(expected) == cls._text(actual)

    def validate_package(
        self,
        package: ReverseCoretaxPackage,
        output_dir: str | Path,
    ) -> ReverseCoretaxRoundtripResult:
        output_path = Path(output_dir)
        result = ReverseCoretaxRoundtripResult(output_dir=output_path)

        if not package.can_export:
            result.issues.append(
                ReverseCoretaxRoundtripIssue(
                    "RCR_001",
                    "ERROR",
                    "ALL",
                    "Paket reverse Coretax belum valid untuk round-trip.",
                )
            )
            return result

        for category in CATEGORY_ORDER:
            config = ReverseCoretaxExcelExporter.CATEGORY_CONFIG[category]
            file_path = output_path / config["filename"]
            expected_headers = list(config["headers"])
            expected_rows = self._expected_rows(package, category)

            result.expected_counts[category] = len(expected_rows)

            if not file_path.is_file():
                result.issues.append(
                    ReverseCoretaxRoundtripIssue(
                        "RCR_101",
                        "ERROR",
                        category,
                        f"File tidak ditemukan: {file_path.name}",
                    )
                )
                continue

            result.checked_files[category] = file_path

            try:
                df = pd.read_excel(file_path, dtype=object)
            except Exception as exc:
                result.issues.append(
                    ReverseCoretaxRoundtripIssue(
                        "RCR_102",
                        "ERROR",
                        category,
                        f"File tidak dapat dibaca: {exc}",
                    )
                )
                continue

            actual_headers = [str(col).strip() for col in df.columns]
            if actual_headers != expected_headers:
                result.issues.append(
                    ReverseCoretaxRoundtripIssue(
                        "RCR_103",
                        "ERROR",
                        category,
                        "Header tidak sesuai kontrak importer internal. "
                        f"Expected={expected_headers}; Actual={actual_headers}",
                    )
                )
                continue

            actual_rows = [
                tuple(row.get(header) for header in expected_headers)
                for _, row in df.iterrows()
                if any(self._text(row.get(header)) for header in expected_headers)
            ]
            result.actual_counts[category] = len(actual_rows)

            if len(actual_rows) != len(expected_rows):
                result.issues.append(
                    ReverseCoretaxRoundtripIssue(
                        "RCR_104",
                        "ERROR",
                        category,
                        f"Jumlah baris berubah: expected {len(expected_rows)}, "
                        f"actual {len(actual_rows)}.",
                    )
                )

            for row_index, (expected, actual) in enumerate(
                zip(expected_rows, actual_rows),
                start=1,
            ):
                for column_index, header in enumerate(expected_headers):
                    if not self._compare_cell(
                        expected[column_index],
                        actual[column_index],
                        header,
                    ):
                        result.issues.append(
                            ReverseCoretaxRoundtripIssue(
                                "RCR_105",
                                "ERROR",
                                category,
                                f"Nilai kolom {header} berubah: "
                                f"expected={expected[column_index]!r}, "
                                f"actual={actual[column_index]!r}.",
                                row_index,
                            )
                        )

        if result.ok:
            counts = ", ".join(
                f"{category}={result.actual_counts.get(category, 0)}"
                for category in CATEGORY_ORDER
            )
            result.issues.append(
                ReverseCoretaxRoundtripIssue(
                    "RCR_INFO",
                    "INFO",
                    "ALL",
                    "Round-trip 6 file Excel lulus tanpa perubahan nilai "
                    f"({counts}).",
                )
            )

        return result

    def validate_active_final(
        self,
        npwp: str,
        tahun_pajak: int,
        output_dir: str | Path,
        *,
        db_path: Optional[str | Path] = None,
    ) -> ReverseCoretaxRoundtripResult:
        package = ReverseCoretaxMappingService(db_path=db_path).build_active_final(
            npwp,
            tahun_pajak,
        )
        return self.validate_package(package, output_dir)
