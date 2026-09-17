from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

from core.mapping.harta_mapper import HartaMappingResult
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.selectable_worksheet_importer import SelectableWorksheetWorkbookImporter
from core.worksheet_workbook_importer import WorksheetWorkbookImportResult


class ThreeSheetWorksheetWorkbookImporter(SelectableWorksheetWorkbookImporter):
    """Importer Kertas Kerja dengan tiga sumber sheet yang eksplisit.

    - Sheet Tahun: identitas + komponen Penghasilan/PPh.
    - SIMULASI I: sumber Original Import Harta + rekonsiliasi.
    - REVISI: struktur Harta sama seperti SIMULASI I dan menjadi kandidat
      Edited / Current pada Worksheet.
    """

    @classmethod
    def suggested_sheets(cls, sheet_names: List[str]) -> Tuple[str, str, str]:
        year_sheet = cls.suggested_sheet(sheet_names)
        simulasi_sheet = next(
            (name for name in sheet_names if str(name).strip().casefold() == "simulasi i"),
            "",
        )
        revisi_sheet = next(
            (name for name in sheet_names if str(name).strip().casefold() == "revisi"),
            "",
        )
        return year_sheet, simulasi_sheet, revisi_sheet

    def parse_selected_triplet(
        self,
        file_path: str | Path,
        year_sheet: str,
        simulasi_sheet: str,
        revisi_sheet: str = "",
    ) -> WorksheetWorkbookImportResult:
        path = Path(file_path)

        # Gunakan parser produksi yang sudah stabil untuk Sheet Tahun dan
        # SIMULASI I. Setelah itu, bila user memilih sumber SIMULASI lain,
        # ganti Harta dengan sheet yang dipilih secara eksplisit.
        result = self.parse_selected(path, year_sheet)
        if result.errors:
            return result

        result.year_sheet_name = str(year_sheet)
        result.simulasi_sheet_name = str(simulasi_sheet or "")
        result.revisi_sheet_name = str(revisi_sheet or "")
        result.revision_harta_rows = []
        result.revision_pipeline_result = None

        excel = pd.ExcelFile(path)
        sheet_names = [str(name) for name in excel.sheet_names]

        default_simulasi = next(
            (name for name in sheet_names if name.strip().casefold() == "simulasi i"),
            "",
        )

        if simulasi_sheet and simulasi_sheet in sheet_names and simulasi_sheet != default_simulasi:
            # Re-parse sumber Harta yang dipilih user tanpa menyentuh data PPh.
            result.harta_rows = []
            simulasi = pd.read_excel(path, sheet_name=simulasi_sheet, header=None, dtype=object)
            self._parse_simulasi_identity(simulasi, result)
            self._parse_harta(simulasi, result)
            self._parse_reconciliation(simulasi, result)

        if result.harta_rows:
            result.pipeline_result = HartaPipelineResult(
                mapping=HartaMappingResult(),
                worksheet_rows=list(result.harta_rows),
                current_year=result.tahun_pajak,
                npwp=result.npwp,
                nama_wp=result.nama_wp,
            )
        else:
            result.pipeline_result = None

        if revisi_sheet and revisi_sheet in sheet_names:
            revision_result = WorksheetWorkbookImportResult(source_path=path)
            revision_result.npwp = result.npwp
            revision_result.nama_wp = result.nama_wp
            revision_result.tahun_pajak = result.tahun_pajak

            revisi = pd.read_excel(path, sheet_name=revisi_sheet, header=None, dtype=object)
            self._parse_harta(revisi, revision_result)
            result.revision_harta_rows = list(revision_result.harta_rows)

            # Warning dari parser REVISI tetap dibawa agar user tahu jika struktur
            # revisi tidak lengkap, tetapi tidak menggagalkan Sheet Tahun utama.
            result.issues.extend(revision_result.warnings)

            if result.revision_harta_rows:
                result.revision_pipeline_result = HartaPipelineResult(
                    mapping=HartaMappingResult(),
                    worksheet_rows=list(result.revision_harta_rows),
                    current_year=result.tahun_pajak,
                    npwp=result.npwp,
                    nama_wp=result.nama_wp,
                )

        return result
