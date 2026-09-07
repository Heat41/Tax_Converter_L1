import re
from pathlib import Path
from typing import List

import pandas as pd

from core.coretax_reader import CoretaxFileInfo, CoretaxReadResult, CorruptedFileError, EmptySheetError


class CoretaxDataSheetAdapter:
    """Adapter untuk workbook Coretax nyata yang memakai sheet DATA.

    Layout yang ditemukan pada file produksi:
      baris 1 : NPWP*        | <nilai NPWP>
      baris 2 : TAHUN PAJAK* | <tahun>
      baris 3 : header tabel kategori
      baris 4+: data harta

    Adapter menormalkan layout tersebut menjadi bentuk tabular yang sudah
    dipakai pipeline lama: NPWP dan Tahun Pajak diulang pada setiap baris.

    Nama header asli dari file produksi tetap dipertahankan. Variasi nama
    kolom, misalnya "Nama Pemilik *" versus "Nama Pemotong Pajak *", ditangani
    oleh alias pada validator/mapper, bukan dengan mengubah header sumber.
    """

    @staticmethod
    def _normalize(value: object) -> str:
        text = "" if value is None else str(value).strip()
        text = re.sub(r"\s+", " ", text)
        return text.rstrip("*").strip().lower()

    @classmethod
    def _find_header_row(cls, matrix: List[List[str]]) -> int:
        for index, row in enumerate(matrix):
            non_empty = [str(value).strip() for value in row if str(value).strip()]
            if len(non_empty) < 2:
                continue
            first = cls._normalize(non_empty[0])
            if first in {"kode", "kode harta"}:
                return index
        raise EmptySheetError(
            "Sheet DATA ditemukan, tetapi baris header tabel harta tidak dapat dikenali."
        )

    @staticmethod
    def _normalize_table_header(value: object) -> str:
        """Rapikan whitespace tanpa mengubah nama header produksi."""
        return "" if value is None else str(value).strip()

    def read(self, info: CoretaxFileInfo, sheet_name: str = "DATA") -> CoretaxReadResult:
        path = Path(info.file_path)
        engine = "openpyxl" if info.file_extension == ".xlsx" else "xlrd"

        try:
            df = pd.read_excel(
                path,
                sheet_name=sheet_name,
                engine=engine,
                dtype=str,
                keep_default_na=False,
                header=None,
            )
        except Exception as exc:
            raise CorruptedFileError(
                f"Gagal membaca sheet DATA pada file '{path.name}': {exc}"
            ) from exc

        matrix: List[List[str]] = []
        for raw_row in df.values.tolist():
            row = [
                "" if value is None or str(value).lower() == "nan" else str(value).strip()
                for value in raw_row
            ]
            matrix.append(row)

        if not matrix:
            raise EmptySheetError(f"Sheet '{sheet_name}' pada file '{path.name}' kosong.")

        header_index = self._find_header_row(matrix)

        metadata = {}
        metadata_labels = {}
        for row in matrix[:header_index]:
            if not row:
                continue
            key = self._normalize(row[0])
            if key in {"npwp", "tahun pajak"}:
                metadata[key] = row[1].strip() if len(row) > 1 else ""
                metadata_labels[key] = row[0].strip()

        npwp = metadata.get("npwp", "")
        tax_year = metadata.get("tahun pajak", "")
        npwp_header = metadata_labels.get("npwp", "NPWP*")
        tax_year_header = metadata_labels.get("tahun pajak", "TAHUN PAJAK*")

        raw_headers = matrix[header_index]
        last_header = -1
        for index, value in enumerate(raw_headers):
            if str(value).strip():
                last_header = index
        if last_header < 0:
            raise EmptySheetError(
                f"Sheet '{sheet_name}' pada file '{path.name}' tidak memiliki header tabel."
            )

        table_headers = [
            self._normalize_table_header(value)
            for value in raw_headers[: last_header + 1]
        ]
        headers = [npwp_header, tax_year_header, *table_headers]

        rows: List[List[str]] = []
        for raw_row in matrix[header_index + 1 :]:
            table_row = [
                str(raw_row[index]).strip() if index < len(raw_row) else ""
                for index in range(len(table_headers))
            ]
            if not any(table_row):
                continue
            rows.append([npwp, tax_year, *table_row])

        return CoretaxReadResult(
            file_path=path,
            file_name=path.name,
            sheet_name=sheet_name,
            headers=headers,
            rows=rows,
            total_rows=len(rows),
            total_columns=len(headers),
            sheets=list(info.sheets),
        )
