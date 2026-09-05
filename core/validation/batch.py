from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import re

from core.coretax_reader import CoretaxReader, CoretaxReaderError
from .engine import ValidationEngine
from .models import BatchImportResult, FileCategoryResult, ValidationIssue, ValidationSeverity
from .rules import CATEGORIES


class CoretaxBatchImporter:
    """Discover, classify and validate up to six Coretax category files."""

    MAX_FILES = 6
    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

    # Longer/specific names must be tested first: otherwise BERGERAK would
    # incorrectly match HARTA TIDAK BERGERAK.
    CATEGORY_KEYWORDS = [
        ("HARTA TIDAK BERGERAK", ("tidak bergerak", "tidak_bergerak")),
        ("KAS SETARA KAS", ("kas setara kas", "kas_setara_kas", "kas")),
        ("PIUTANG", ("piutang",)),
        ("INVESTASI", ("investasi",)),
        ("HARTA BERGERAK", ("harta bergerak", "harta_bergerak", "bergerak")),
        ("LAINNYA", ("lainnya", "lainnya")),
    ]

    SHEET_NAMES = {
        "KAS SETARA KAS": "KAS SETARA KAS",
        "PIUTANG": "PIUTANG",
        "INVESTASI": "INVESTASI",
        "HARTA BERGERAK": "HARTA BERGERAK",
        "HARTA TIDAK BERGERAK": "HARTA TIDAK BERGERAK",
        "LAINNYA": "LAINNYA",
    }

    def __init__(self, reader: Optional[CoretaxReader] = None, validator: Optional[ValidationEngine] = None):
        self.reader = reader or CoretaxReader()
        self.validator = validator or ValidationEngine()

    @staticmethod
    def _normalized_filename(path: Path) -> str:
        return re.sub(r"[_\-]+", " ", path.stem.lower())

    def detect_category(self, file_path: Path) -> Optional[str]:
        name = self._normalized_filename(file_path)
        for category, keywords in self.CATEGORY_KEYWORDS:
            if any(keyword in name for keyword in keywords):
                return category

        # Filename is the primary signal. Workbook structure is the fallback.
        try:
            info = self.reader.inspect_file(file_path)
            normalized_sheets = {re.sub(r"\s+", " ", s.strip().upper()) for s in info.sheets}
            for category in CATEGORIES:
                expected = self.SHEET_NAMES[category]
                if expected in normalized_sheets:
                    return category
        except Exception:
            return None
        return None

    def discover_files(self, folder_path: Path) -> List[Path]:
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Folder tidak ditemukan atau bukan folder: '{folder}'")
        return sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def classify_files(self, files: Sequence[Path]) -> BatchImportResult:
        result = BatchImportResult(selected_files=[Path(p).resolve() for p in files])
        if len(result.selected_files) > self.MAX_FILES:
            result.errors.append(ValidationIssue(
                None, None, "MAX_FILES_EXCEEDED", ValidationSeverity.ERROR,
                f"Maksimal {self.MAX_FILES} file kategori Coretax dapat diproses sekaligus.",
                len(result.selected_files),
            ))
            return result

        candidates: Dict[str, List[Path]] = {category: [] for category in CATEGORIES}
        for path in result.selected_files:
            category = self.detect_category(path)
            if category is None:
                result.unknown_files.append(path)
            else:
                candidates[category].append(path)

        for category in CATEGORIES:
            matches = candidates[category]
            if len(matches) == 1:
                result.category_files[category] = matches[0]
                result.category_results[category] = FileCategoryResult(
                    category=category, file_path=matches[0], status="FOUND",
                )
            elif len(matches) > 1:
                result.duplicate_categories[category] = matches
                result.category_results[category] = FileCategoryResult(
                    category=category, status="DUPLICATE",
                    message="Lebih dari satu file ditemukan untuk kategori ini.",
                )
            else:
                result.missing_categories.append(category)
                result.category_results[category] = FileCategoryResult(
                    category=category, status="MISSING",
                )

        for path in result.unknown_files:
            result.warnings.append(ValidationIssue(
                None, None, "UNKNOWN_CATEGORY", ValidationSeverity.WARNING,
                f"File tidak dapat dikenali sebagai salah satu dari 6 kategori Coretax: {path.name}",
                str(path),
            ))

        for category, paths in result.duplicate_categories.items():
            result.errors.append(ValidationIssue(
                None, None, "DUPLICATE_CATEGORY", ValidationSeverity.ERROR,
                f"Ditemukan {len(paths)} file untuk kategori {category}. Pilih satu file saja.",
                "; ".join(str(p) for p in paths),
            ))
        return result

    @staticmethod
    def _looks_like_rulebook(headers: Iterable[str]) -> bool:
        normalized = {re.sub(r"\s+", " ", str(h).strip().lower()) for h in headers}
        markers = {
            "kolom pada excel",
            "kolom pada xml",
            "petunjuk pengisian",
            "contoh pengisian",
            "validasi",
        }
        return len(normalized & markers) >= 3

    @staticmethod
    def _looks_like_header(headers: Iterable[str], category: str) -> bool:
        expected = {
            "npwp", "npwp *", "npwp*", "tahun pajak", "tahun pajak *", "tahun pajak*",
            "kode", "kode *", "kode*", "kode harta *",
        }
        normalized = {str(h).strip().lower() for h in headers}
        return len(normalized & expected) >= 2

    def _read_category(self, category: str, path: Path) -> Tuple[Optional[object], bool, bool, Optional[str]]:
        info = self.reader.inspect_file(path)
        if not info.is_excel:
            read_result = self.reader.read(path)
            return read_result, False, read_result.total_rows == 0, None

        category_sheet = self.SHEET_NAMES[category]
        matching = [s for s in info.sheets if re.sub(r"\s+", " ", s.strip().upper()) == category_sheet]
        if not matching:
            # A populated export may not use the specification sheet name.
            # Fall back to the first sheet only when it resembles a data table.
            for sheet in info.sheets:
                candidate = self.reader.read(path, sheet_name=sheet)
                if self._looks_like_header(candidate.headers, category):
                    return candidate, False, candidate.total_rows == 0, None
            return None, True, True, "Tidak ditemukan sheet data kategori yang dikenali."

        candidate = self.reader.read(path, sheet_name=matching[0])
        if self._looks_like_rulebook(candidate.headers):
            # The official six workbooks inspected in Stage 3A are specification
            # templates. Example values must never be validated as taxpayer data.
            return None, True, True, "Workbook terdeteksi sebagai template/spesifikasi Coretax; tidak ada data WP untuk divalidasi."

        return candidate, False, candidate.total_rows == 0, None

    def validate(self, files: Sequence[Path], *, spt_year: Optional[int] = None) -> BatchImportResult:
        result = self.classify_files(files)
        if result.errors:
            return result

        for category, path in result.category_files.items():
            category_result = result.category_results[category]
            try:
                read_result, is_template, is_nihil, message = self._read_category(category, path)
                category_result.read_result = read_result
                category_result.is_template = is_template
                category_result.is_nihil = is_nihil

                if message and read_result is None:
                    category_result.status = "NIHIL"
                    category_result.message = message
                    continue

                if read_result is None:
                    category_result.status = "NIHIL"
                    continue

                validation = self.validator.validate_rows(
                    category, read_result.headers, read_result.rows, spt_year=spt_year,
                )
                category_result.validation = validation
                category_result.status = "VALID" if validation.is_valid else "INVALID"
                category_result.message = "Valid" if validation.is_valid else "Terdapat kesalahan validasi."
                result.errors.extend(validation.errors)
                result.warnings.extend(validation.warnings)
                result.total_rows += validation.total_rows
                result.valid_rows += validation.valid_rows
                result.invalid_rows += validation.invalid_rows
            except (CoretaxReaderError, FileNotFoundError) as exc:
                category_result.status = "ERROR"
                category_result.message = str(exc)
                result.errors.append(ValidationIssue(
                    None, None, "FILE_READ_ERROR", ValidationSeverity.ERROR,
                    f"Gagal membaca file kategori {category}: {exc}", str(path),
                ))
            except Exception as exc:
                category_result.status = "ERROR"
                category_result.message = str(exc)
                result.errors.append(ValidationIssue(
                    None, None, "UNEXPECTED_ERROR", ValidationSeverity.ERROR,
                    f"Kesalahan tidak terduga pada kategori {category}: {exc}", str(path),
                ))

        return result
