from pathlib import Path
import tempfile

import pandas as pd

from core.selectable_worksheet_importer import SelectableWorksheetWorkbookImporter


def _annual(name, npwp):
    rows = [[None] * 8 for _ in range(12)]
    rows[0][0] = "KERTAS KERJA SPT TAHUNAN"
    rows[1][0] = "NAMA"
    rows[1][1] = name
    rows[2][0] = "NPWP"
    rows[2][1] = npwp
    rows[5][0] = "PTKP"
    rows[5][5] = "TK/0"
    return pd.DataFrame(rows)


def _simulasi():
    rows = [[None] * 12 for _ in range(25)]
    headers = [
        "NO", "KODE EFORM", "KODE CT", "NAMA HARTA", "NOMOR AKUN / KETERANGAN",
        "ATAS NAMA", "NAMA BANK", "TH PEROLEHAN", "2023", "2024",
    ]
    for col, value in enumerate(headers):
        rows[10][col] = value
    rows[11][:10] = [1, "014", "0104", "Deposito", "123", "WP TEST", "BRI", 2022, 100, 200]
    rows[12][0] = "TOTAL HARTA"
    return pd.DataFrame(rows)


def test_user_selected_sheet_is_used_instead_of_latest_auto_sheet():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "worksheet.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            _annual("WP 2024", "1111111111111111").to_excel(writer, sheet_name="2024", index=False, header=False)
            _annual("WP 2025", "2222222222222222").to_excel(writer, sheet_name="2025", index=False, header=False)
            _simulasi().to_excel(writer, sheet_name="SIMULASI I", index=False, header=False)

        importer = SelectableWorksheetWorkbookImporter()
        sheets = importer.list_sheets(path)
        assert importer.suggested_sheet(sheets) == "2025"

        result = importer.parse_selected(path, "2024")
        assert result.tahun_pajak == 2024
        assert result.nama_wp == "WP 2024"
        assert result.npwp == "1111111111111111"
