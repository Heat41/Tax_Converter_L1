from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pandas as pd

from core.mapping.harta_mapper import HartaMappingResult
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_workbook_generic import GenericWorksheetWorkbookImporter
from core.worksheet_workbook_importer import (
    WorksheetWorkbookImportIssue,
    WorksheetWorkbookImportResult,
)


class SelectableWorksheetWorkbookImporter(GenericWorksheetWorkbookImporter):
    """Importer Kertas Kerja dengan sheet utama dipilih user.

    Auto-detect hanya dipakai untuk memberi saran awal di UI. Parsing selalu
    memakai sheet yang dipilih user, sedangkan SIMULASI I tetap menjadi sumber Harta.
    """

    def list_sheets(self, file_path: str | Path) -> List[str]:
        path = Path(file_path)
        excel = pd.ExcelFile(path)
        return [str(name) for name in excel.sheet_names]

    @staticmethod
    def suggested_sheet(sheet_names: List[str]) -> str:
        candidates = []
        for name in sheet_names:
            match = re.search(r"\b(20\d{2})\b", str(name))
            if match:
                candidates.append((int(match.group(1)), str(name)))
        return max(candidates, default=(0, ""))[1]

    def parse_selected(
        self,
        file_path: str | Path,
        sheet_name: str,
    ) -> WorksheetWorkbookImportResult:
        path = Path(file_path)
        result = WorksheetWorkbookImportResult(source_path=path)

        if not path.exists():
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_001", "ERROR", "File kertas kerja tidak ditemukan.")
            )
            return result
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_002", "ERROR", "Kertas kerja harus berupa file Excel .xlsx/.xls.")
            )
            return result

        try:
            excel = pd.ExcelFile(path)
        except Exception as exc:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_003", "ERROR", f"Workbook tidak dapat dibaca: {exc}")
            )
            return result

        if sheet_name not in excel.sheet_names:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_004",
                    "ERROR",
                    f"Sheet '{sheet_name}' tidak ditemukan pada workbook.",
                )
            )
            return result

        try:
            annual = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)
        except Exception as exc:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_003", "ERROR", f"Sheet tidak dapat dibaca: {exc}")
            )
            return result

        result.tahun_pajak = self._detect_year(sheet_name, annual)
        if not result.tahun_pajak:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_004",
                    "ERROR",
                    "Tahun pajak tidak dapat dikenali dari sheet yang dipilih.",
                )
            )
            return result

        self._parse_identity(annual, result)
        # Kertas Kerja tidak lagi menjadi sumber Bupot utama.
        self._parse_pph_components(annual, result)

        simulasi_name = next(
            (name for name in excel.sheet_names if str(name).strip().casefold() == "simulasi i"),
            None,
        )
        if simulasi_name is not None:
            simulasi = pd.read_excel(path, sheet_name=simulasi_name, header=None, dtype=object)
            self._parse_simulasi_identity(simulasi, result)
            self._parse_harta(simulasi, result)
            self._parse_reconciliation(simulasi, result)
        else:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_101",
                    "WARNING",
                    "Sheet SIMULASI I tidak ditemukan. Harta harus dilengkapi di aplikasi.",
                )
            )

        if not result.npwp:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_005", "ERROR", "NPWP tidak ditemukan pada kertas kerja.")
            )
        if not result.nama_wp:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_102", "WARNING", "Nama Wajib Pajak tidak ditemukan pada kertas kerja.")
            )

        if result.harta_rows:
            result.pipeline_result = HartaPipelineResult(
                mapping=HartaMappingResult(),
                worksheet_rows=list(result.harta_rows),
                current_year=result.tahun_pajak,
                npwp=result.npwp,
                nama_wp=result.nama_wp,
            )
        else:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_103",
                    "WARNING",
                    "Tidak ada baris Harta pada SIMULASI I.",
                )
            )

        return result

    @staticmethod
    def _detect_year(sheet_name: str, df) -> int:
        match = re.search(r"\b(20\d{2})\b", str(sheet_name))
        if match:
            return int(match.group(1))

        for row in range(min(len(df), 20)):
            for col in range(min(df.shape[1], 10)):
                text = str(df.iat[row, col] or "")
                match = re.search(r"\b(20\d{2})\b", text)
                if match:
                    return int(match.group(1))
        return 0
