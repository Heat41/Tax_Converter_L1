from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from core.mapping.legacy_1770iv import Legacy1770IVRow


@dataclass(frozen=True)
class Legacy1770IVWriteResult:
    output_path: Path
    sheet_name: str
    header_row: int
    start_row: int
    written_rows: int
    total_acquisition_cost: float


class Legacy1770IVExcelWriter:
    """Write canonical 1770-IV rows into an Excel template safely.

    The writer locates the legacy asset table from its headers instead of
    depending on hard-coded Excel coordinates. Existing workbook styles,
    formulas, merged cells and unrelated sheets are preserved by openpyxl.
    """

    REQUIRED_HEADERS = {
        "Kode Harta": ("kode harta", "kode"),
        "Nama Harta": ("nama harta", "nama/jenis harta", "nama / jenis harta"),
        "Tahun Perolehan": ("tahun perolehan", "tahun"),
        "Harga Perolehan": ("harga perolehan", "nilai perolehan"),
        "Keterangan": ("keterangan",),
    }

    DEFAULT_SHEET_HINTS = ("1770-IV", "1770 IV", "1770IV", "IV")

    def write(
        self,
        template_path: Path | str,
        output_path: Path | str,
        rows: Iterable[Legacy1770IVRow],
        *,
        sheet_name: Optional[str] = None,
    ) -> Legacy1770IVWriteResult:
        template = Path(template_path).resolve()
        output = Path(output_path).resolve()

        if not template.exists() or not template.is_file():
            raise FileNotFoundError(f"Template Excel tidak ditemukan: '{template}'")
        if template.suffix.lower() not in {".xlsx", ".xlsm"}:
            raise ValueError("Stage 3E hanya mendukung template .xlsx atau .xlsm.")

        keep_vba = template.suffix.lower() == ".xlsm"
        workbook = load_workbook(template, keep_vba=keep_vba)
        worksheet, header_row, columns = self._locate_table(workbook, sheet_name=sheet_name)

        normalized_rows = list(rows)
        start_row = header_row + 1
        footer_row = self._find_footer_row(worksheet, start_row, columns)

        if footer_row is not None:
            available_rows = max(0, footer_row - start_row)
            missing_rows = max(0, len(normalized_rows) - available_rows)
            if missing_rows:
                worksheet.insert_rows(footer_row, amount=missing_rows)
                self._copy_template_row_style(
                    worksheet,
                    source_row=max(start_row, footer_row - 1),
                    target_start=footer_row,
                    count=missing_rows,
                    columns=columns,
                )
        elif normalized_rows:
            # Ensure rows beyond current max_row inherit the first available
            # data-row style when a footer/table boundary cannot be identified.
            last_needed = start_row + len(normalized_rows) - 1
            if last_needed > worksheet.max_row:
                self._copy_template_row_style(
                    worksheet,
                    source_row=start_row,
                    target_start=worksheet.max_row + 1,
                    count=last_needed - worksheet.max_row,
                    columns=columns,
                )

        self._clear_existing_table_values(worksheet, start_row, footer_row, columns)
        self._write_rows(worksheet, start_row, normalized_rows, columns)

        output.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(output)

        return Legacy1770IVWriteResult(
            output_path=output,
            sheet_name=worksheet.title,
            header_row=header_row,
            start_row=start_row,
            written_rows=len(normalized_rows),
            total_acquisition_cost=float(sum(row.harga_perolehan for row in normalized_rows)),
        )

    def _locate_table(
        self,
        workbook,
        *,
        sheet_name: Optional[str],
    ) -> Tuple[Worksheet, int, Dict[str, int]]:
        candidates: Sequence[Worksheet]
        if sheet_name:
            if sheet_name not in workbook.sheetnames:
                raise ValueError(
                    f"Sheet '{sheet_name}' tidak ditemukan. Sheet tersedia: {', '.join(workbook.sheetnames)}"
                )
            candidates = [workbook[sheet_name]]
        else:
            preferred: List[Worksheet] = []
            others: List[Worksheet] = []
            for title in workbook.sheetnames:
                ws = workbook[title]
                title_norm = self._normalize(title)
                if any(self._normalize(hint) in title_norm for hint in self.DEFAULT_SHEET_HINTS):
                    preferred.append(ws)
                else:
                    others.append(ws)
            candidates = [*preferred, *others]

        for ws in candidates:
            located = self._find_header_row(ws)
            if located is not None:
                header_row, columns = located
                return ws, header_row, columns

        raise ValueError(
            "Tabel 1770-IV tidak ditemukan. Pastikan template memiliki header "
            "Kode Harta, Nama Harta, Tahun Perolehan, Harga Perolehan, dan Keterangan."
        )

    def _find_header_row(self, ws: Worksheet) -> Optional[Tuple[int, Dict[str, int]]]:
        max_scan_row = min(ws.max_row, 150)
        max_scan_col = min(ws.max_column, 40)

        for row_idx in range(1, max_scan_row + 1):
            columns: Dict[str, int] = {}
            for col_idx in range(1, max_scan_col + 1):
                value = ws.cell(row=row_idx, column=col_idx).value
                normalized = self._normalize(value)
                if not normalized:
                    continue

                for canonical, aliases in self.REQUIRED_HEADERS.items():
                    if canonical in columns:
                        continue
                    if any(normalized == self._normalize(alias) for alias in aliases):
                        columns[canonical] = col_idx
                        break

            if len(columns) == len(self.REQUIRED_HEADERS):
                return row_idx, columns

        return None

    def _find_footer_row(
        self,
        ws: Worksheet,
        start_row: int,
        columns: Dict[str, int],
    ) -> Optional[int]:
        relevant_cols = sorted(columns.values())
        for row_idx in range(start_row, ws.max_row + 1):
            values = [ws.cell(row=row_idx, column=col).value for col in relevant_cols]
            if not any(value not in (None, "") for value in values):
                continue

            if self._looks_like_data_row(values):
                continue

            # Formula or label rows below the table are considered footer.
            if any(self._is_formula(value) for value in values):
                return row_idx

            joined = " ".join(self._normalize(v) for v in values if v not in (None, ""))
            if any(marker in joined for marker in ("jumlah", "total", "subtotal")):
                return row_idx

        return None

    @staticmethod
    def _looks_like_data_row(values: Sequence[object]) -> bool:
        populated = [v for v in values if v not in (None, "")]
        return len(populated) >= 2

    @staticmethod
    def _is_formula(value: object) -> bool:
        return isinstance(value, str) and value.startswith("=")

    def _clear_existing_table_values(
        self,
        ws: Worksheet,
        start_row: int,
        footer_row: Optional[int],
        columns: Dict[str, int],
    ) -> None:
        end_row = (footer_row - 1) if footer_row is not None else ws.max_row
        for row_idx in range(start_row, end_row + 1):
            for col_idx in columns.values():
                cell = ws.cell(row=row_idx, column=col_idx)
                if self._is_formula(cell.value):
                    continue
                cell.value = None

    def _write_rows(
        self,
        ws: Worksheet,
        start_row: int,
        rows: Sequence[Legacy1770IVRow],
        columns: Dict[str, int],
    ) -> None:
        for offset, row in enumerate(rows):
            row_idx = start_row + offset
            values = row.as_dict()
            for header, col_idx in columns.items():
                ws.cell(row=row_idx, column=col_idx).value = values[header]

    def _copy_template_row_style(
        self,
        ws: Worksheet,
        *,
        source_row: int,
        target_start: int,
        count: int,
        columns: Dict[str, int],
    ) -> None:
        if count <= 0 or source_row < 1:
            return

        max_col = max(columns.values())
        for offset in range(count):
            target_row = target_start + offset
            for col_idx in range(1, max_col + 1):
                source = ws.cell(row=source_row, column=col_idx)
                target = ws.cell(row=target_row, column=col_idx)
                self._copy_cell_style(source, target)
            if source_row in ws.row_dimensions:
                ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height

    @staticmethod
    def _copy_cell_style(source: Cell, target: Cell) -> None:
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
        if source.font:
            target.font = copy(source.font)
        if source.fill:
            target.fill = copy(source.fill)
        if source.border:
            target.border = copy(source.border)
        if source.alignment:
            target.alignment = copy(source.alignment)
        if source.protection:
            target.protection = copy(source.protection)

    @staticmethod
    def _normalize(value: object) -> str:
        if value is None:
            return ""
        return " ".join(str(value).replace("\n", " ").strip().lower().split())
