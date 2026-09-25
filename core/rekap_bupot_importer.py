from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from core.worksheet_pph_state import WorksheetBupotRow, WorksheetPPhStateStore


@dataclass
class RekapBupotImportResult:
    source_path: Path
    rows: List[WorksheetBupotRow] = field(default_factory=list)
    sheet_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return bool(self.rows) and not self.errors


class RekapBupotImporter:
    """Importer Rekap Bupot dengan kontrak header mengikuti file golden reference."""

    REQUIRED_ANCHORS = {
        "JENIS BUPOT",
        "NO BUKPOT",
        "BRUTO",
        "PENGURANG BRUTO",
        "PPH",
    }

    HEADER_TO_FIELD = {
        "JENIS BUPOT": "jenis",
        "NO BUKPOT": "no_bupot",
        "MASA": "masa",
        "TAHUN": "tahun",
        "SIFAT": "sifat",
        "STATUS": "status",
        "NPWP PENERIMA": "npwp_penerima",
        "NAMA PENERIMA": "nama_penerima",
        "FASILITAS": "fasilitas",
        "JENIS PPH": "jenis_pph",
        "KOP": "kop",
        "BRUTO": "bruto",
        "DPP PERSEN": "dpp_persen",
        "TARIF": "tarif",
        "PENGURANG BRUTO": "pengurang",
        "PPH": "pph_dipotong",
        "BUKTI": "bukti",
        "NO BUKTI": "no_bukti",
        "TANGGAL BUKTI": "tanggal_bukti",
        "NPWP PEMOTONG": "npwp_pemotong",
        "NAMA PEMOTONG": "nama_pemotong",
        "TANGGAL PEMOTONGAN": "tanggal_pemotongan",
        "TGL PEMOTONGAN": "tanggal_pemotongan",
        "MEKANISME SP2D": "mekanisme_sp2d",
        "NO SP2D": "no_sp2d",
    }

    def __init__(self, pph_store: Optional[WorksheetPPhStateStore] = None):
        self.pph_store = pph_store or WorksheetPPhStateStore()

    @staticmethod
    def _norm(value) -> str:
        return " ".join(str(value or "").strip().upper().split())

    @staticmethod
    def _text(value) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _number(value) -> float:
        if value is None or pd.isna(value) or value == "":
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace("Rp", "").replace(" ", "").strip()
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def parse(self, file_path: str | Path) -> RekapBupotImportResult:
        path = Path(file_path)
        result = RekapBupotImportResult(source_path=path)

        if not path.exists():
            result.errors.append("File Rekap Bupot tidak ditemukan.")
            return result
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            result.errors.append("Rekap Bupot harus berupa file Excel .xlsx/.xls.")
            return result

        best_rows: List[WorksheetBupotRow] = []
        best_sheet = ""
        best_warning = ""

        try:
            with pd.ExcelFile(path) as excel:
                sheet_names = list(excel.sheet_names)
                for sheet in sheet_names:
                    try:
                        df = pd.read_excel(
                            excel,
                            sheet_name=sheet,
                            header=None,
                            dtype=object,
                        )
                    except Exception:
                        continue

                    parsed, warning = self._parse_sheet(df)
                    if len(parsed) > len(best_rows):
                        best_rows = parsed
                        best_sheet = str(sheet)
                        best_warning = warning
        except Exception as exc:
            result.errors.append(f"Workbook Rekap Bupot tidak dapat dibaca: {exc}")
            return result

        if not best_rows:
            result.errors.append(
                "Tabel Rekap Bupot tidak ditemukan. Header anchor wajib: "
                + ", ".join(sorted(self.REQUIRED_ANCHORS))
            )
            return result

        result.rows = best_rows
        result.sheet_name = best_sheet
        if best_warning:
            result.warnings.append(best_warning)
        return result

    def _parse_sheet(self, df) -> tuple[List[WorksheetBupotRow], str]:
        for row_idx in range(min(len(df), 30)):
            headers = {
                self._norm(df.iat[row_idx, col]): col
                for col in range(df.shape[1])
                if self._text(df.iat[row_idx, col])
            }
            if not self.REQUIRED_ANCHORS.issubset(headers):
                continue

            rows: List[WorksheetBupotRow] = []
            for data_row in range(row_idx + 1, len(df)):
                if not self._text(df.iat[data_row, headers["NO BUKPOT"]]):
                    continue
                values: Dict[str, object] = {}
                for header, field in self.HEADER_TO_FIELD.items():
                    col = headers.get(header)
                    if col is None:
                        continue
                    value = df.iat[data_row, col]
                    if field in {"bruto", "pengurang", "pph_dipotong", "dpp_persen", "tarif"}:
                        values[field] = self._number(value)
                    else:
                        values[field] = self._text(value)

                pemotong = str(values.get("npwp_pemotong") or "")
                values["npwp_pemberi_kerja"] = pemotong
                rows.append(WorksheetBupotRow(**values))

            missing = sorted(set(self.HEADER_TO_FIELD) - set(headers))
            warning = ""
            if missing:
                warning = "Kolom pendukung tidak ditemukan: " + ", ".join(missing)
            return rows, warning

        return [], ""

    def persist_replace(
        self,
        *,
        npwp: str,
        tahun_pajak: int,
        rows: List[WorksheetBupotRow],
    ) -> None:
        existing = self.pph_store.load(npwp, tahun_pajak)
        components = dict(existing.components) if existing is not None else {}
        self.pph_store.save(
            npwp=npwp,
            tahun_pajak=tahun_pajak,
            bupot_rows=list(rows),
            components=components,
        )

    def persist_merge(
        self,
        *,
        npwp: str,
        tahun_pajak: int,
        rows: List[WorksheetBupotRow],
    ) -> int:
        existing = self.pph_store.load(npwp, tahun_pajak)
        current = list(existing.bupot_rows) if existing is not None else []
        components = dict(existing.components) if existing is not None else {}

        merged = {self._identity_key(row): row for row in current}
        before = len(merged)
        for row in rows:
            merged[self._identity_key(row)] = row

        final_rows = list(merged.values())
        self.pph_store.save(
            npwp=npwp,
            tahun_pajak=tahun_pajak,
            bupot_rows=final_rows,
            components=components,
        )
        return len(merged) - before

    @staticmethod
    def _identity_key(row: WorksheetBupotRow) -> tuple:
        return (
            str(row.jenis or "").strip().upper(),
            str(row.no_bupot or "").strip().upper(),
            str(row.npwp_pemotong or row.npwp_pemberi_kerja or "").strip(),
        )
