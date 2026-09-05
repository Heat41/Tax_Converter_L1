from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, List, Optional, Union
import pandas as pd


class CoretaxReaderError(Exception):
    """Base exception for all CoretaxReader errors."""
    pass


class UnsupportedFileFormatError(CoretaxReaderError):
    """Raised when the file format or extension is not supported."""
    pass


class EmptyFileError(CoretaxReaderError):
    """Raised when the selected file is completely empty."""
    pass


class EmptySheetError(CoretaxReaderError):
    """Raised when the selected Excel sheet contains no data or headers."""
    pass


class CorruptedFileError(CoretaxReaderError):
    """Raised when the file cannot be parsed due to corruption or invalid format."""
    pass


@dataclass
class CoretaxFileInfo:
    file_path: Path
    file_name: str
    file_extension: str
    sheets: List[str] = field(default_factory=list)
    is_excel: bool = False
    is_csv: bool = False


@dataclass
class CoretaxReadResult:
    file_path: Path
    file_name: str
    sheet_name: Optional[str]
    headers: List[str]
    rows: List[List[Any]]
    total_rows: int
    total_columns: int
    sheets: List[str] = field(default_factory=list)


class CoretaxReader:
    """
    Reader untuk membaca file ekspor Coretax (Excel .xlsx/.xls dan .csv).

    Bertanggung jawab untuk:
    - Memeriksa keabsahan file dan mendeteksi sheet yang tersedia.
    - Membaca header dan baris data secara dinamis.
    - Mempertahankan tipe data teks/kode (seperti NPWP atau kode berawalan 0).
    - Menangani error secara aman tanpa menyebabkan crash pada aplikasi.
    """

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

    def inspect_file(self, file_path: Union[str, Path]) -> CoretaxFileInfo:
        """
        Memeriksa metadata file (apakah file ada, extension valid, dan daftar sheet jika Excel).
        """
        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: '{path}'")

        if not path.is_file():
            raise CoretaxReaderError(f"Path bukan merupakan file yang valid: '{path}'")

        if path.stat().st_size == 0:
            raise EmptyFileError(f"File kosong (0 byte): '{path.name}'")

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            supported_str = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise UnsupportedFileFormatError(
                f"Format file '{ext}' tidak didukung. Format yang didukung: {supported_str}"
            )

        is_excel = ext in {".xlsx", ".xls"}
        is_csv = ext == ".csv"
        sheets: List[str] = []

        if is_excel:
            try:
                engine = "openpyxl" if ext == ".xlsx" else "xlrd"
                # Menggunakan pd.ExcelFile untuk inspeksi sheet names tanpa meload seluruh data
                with pd.ExcelFile(path, engine=engine) as excel_file:
                    sheets = list(excel_file.sheet_names)
                if not sheets:
                    raise EmptyFileError(f"Workbook Excel tidak memiliki sheet: '{path.name}'")
            except CoretaxReaderError:
                raise
            except Exception as e:
                raise CorruptedFileError(
                    f"File Excel rusak atau tidak dapat dibuka: {e}"
                ) from e

        return CoretaxFileInfo(
            file_path=path,
            file_name=path.name,
            file_extension=ext,
            sheets=sheets,
            is_excel=is_excel,
            is_csv=is_csv,
        )

    def read(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
    ) -> CoretaxReadResult:
        """
        Membaca isi file Coretax dan mengembalikan struktur data lengkap.

        Args:
            file_path: Path ke file (.xlsx, .xls, atau .csv).
            sheet_name: Nama atau indeks sheet jika file adalah Excel (default: sheet pertama).

        Returns:
            CoretaxReadResult berisi metadata, headers, dan rows.
        """
        info = self.inspect_file(file_path)

        if info.is_csv:
            return self._read_csv(info)
        elif info.is_excel:
            return self._read_excel(info, sheet_name)
        else:
            raise UnsupportedFileFormatError(
                f"Format file '{info.file_extension}' tidak didukung."
            )

    def _read_csv(self, info: CoretaxFileInfo) -> CoretaxReadResult:
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        df = None
        last_error = None

        for enc in encodings:
            try:
                df = pd.read_csv(
                    info.file_path,
                    dtype=str,
                    keep_default_na=False,
                    encoding=enc,
                )
                break
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
            except pd.errors.EmptyDataError:
                raise EmptyFileError(f"File CSV kosong: '{info.file_name}'")
            except Exception as e:
                raise CorruptedFileError(f"Gagal membaca file CSV: {e}") from e

        if df is None:
            raise CorruptedFileError(
                f"Tidak dapat membaca encoding file CSV: {last_error}"
            )

        return self._extract_result(info, df, sheet_name=None)

    def _read_excel(
        self,
        info: CoretaxFileInfo,
        sheet_name: Optional[Union[str, int]] = None,
    ) -> CoretaxReadResult:
        target_sheet: Union[str, int] = 0
        if sheet_name is not None:
            if isinstance(sheet_name, str):
                if sheet_name not in info.sheets:
                    raise CoretaxReaderError(
                        f"Sheet '{sheet_name}' tidak ditemukan pada workbook. Sheet yang ada: {', '.join(info.sheets)}"
                    )
                target_sheet = sheet_name
            else:
                target_sheet = sheet_name

        engine = "openpyxl" if info.file_extension == ".xlsx" else "xlrd"
        try:
            df = pd.read_excel(
                info.file_path,
                sheet_name=target_sheet,
                engine=engine,
                dtype=str,
                keep_default_na=False,
            )
        except Exception as e:
            raise CorruptedFileError(
                f"Gagal membaca sheet '{target_sheet}' pada file Excel: {e}"
            ) from e

        # Resolve actual sheet name string
        resolved_sheet_name: Optional[str] = None
        if isinstance(target_sheet, str):
            resolved_sheet_name = target_sheet
        elif isinstance(target_sheet, int) and 0 <= target_sheet < len(info.sheets):
            resolved_sheet_name = info.sheets[target_sheet]
        elif info.sheets:
            resolved_sheet_name = info.sheets[0]

        return self._extract_result(info, df, sheet_name=resolved_sheet_name)

    def _extract_result(
        self,
        info: CoretaxFileInfo,
        df: pd.DataFrame,
        sheet_name: Optional[str] = None,
    ) -> CoretaxReadResult:
        if df.empty and len(df.columns) == 0:
            if info.is_excel:
                raise EmptySheetError(
                    f"Sheet '{sheet_name or 'Sheet1'}' pada file '{info.file_name}' kosong."
                )
            raise EmptyFileError(f"File '{info.file_name}' tidak memiliki data.")

        # Clean headers
        headers = [str(col).strip() for col in df.columns]

        # Check if table only has empty Unnamed columns and no rows
        if len(df) == 0 and all(h.startswith("Unnamed:") for h in headers):
            if info.is_excel:
                raise EmptySheetError(
                    f"Sheet '{sheet_name or 'Sheet1'}' tidak memiliki data atau header yang valid."
                )
            raise EmptyFileError(f"File '{info.file_name}' tidak memiliki data atau header yang valid.")

        # Convert rows to list of strings, stripping None/nan values
        raw_rows = df.values.tolist()
        cleaned_rows: List[List[str]] = []

        for row in raw_rows:
            cleaned_row = [
                "" if val is None or val == "nan" or val == "NaN" else str(val).strip()
                for val in row
            ]
            # Skip rows where all cells are blank
            if any(cell != "" for cell in cleaned_row):
                cleaned_rows.append(cleaned_row)

        return CoretaxReadResult(
            file_path=info.file_path,
            file_name=info.file_name,
            sheet_name=sheet_name,
            headers=headers,
            rows=cleaned_rows,
            total_rows=len(cleaned_rows),
            total_columns=len(headers),
            sheets=info.sheets,
        )
