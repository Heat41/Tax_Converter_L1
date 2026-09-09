from pathlib import Path
from unittest.mock import patch

import pandas as pd

from core.worksheet_workbook_generic import GenericWorksheetWorkbookImporter


def _annual_generic():
    rows = [[None] * 18 for _ in range(45)]
    rows[2][2], rows[2][3] = "Nama Wajib Pajak", "CONTOH WP"
    rows[3][2], rows[3][3] = "NPWP Wajib Pajak", "12.345.678.9-012.345"

    # Blok pertama memakai alias dan posisi berbeda.
    headers = [
        "NO", "JENIS BUPOT", "NPWP PEMOTONG", "NOMOR BUKTI POTONG",
        "PENGHASILAN BRUTO", "BIAYA PENGURANG", "NETTO",
    ]
    for offset, value in enumerate(headers, start=3):
        rows[8][offset] = value

    # Header duplikat lain di kanan tanpa data.
    rows[8][12] = "JENIS"
    rows[8][13] = "NPWP PEMBERI KERJA"
    rows[8][14] = "NO BUPOT"
    rows[8][15] = "BRUTO"
    rows[8][16] = "PENGURANG"

    values = [1, "BP21", "0011050945093000", "GEN-001", 10_000_000, 2_000_000, 8_000_000]
    for offset, value in enumerate(values, start=3):
        rows[9][offset] = value
    rows[10][3] = "TOTAL"
    return pd.DataFrame(rows)


def _simulasi_generic():
    rows = [[None] * 14 for _ in range(35)]
    headers = [
        "NO", "KODE LAMA", "KODE CORETAX", "URAIAN HARTA",
        "REKENING / KETERANGAN", "A/N", "BANK", "TAHUN PEROLEHAN",
        "2024", "2025",
    ]
    for col, value in enumerate(headers, start=2):
        rows[10][col] = value
    values = [1, "", "0104", "Deposito", "123", "CONTOH WP", "BRI", 2022, 5_000_000, 6_000_000]
    for col, value in enumerate(values, start=2):
        rows[11][col] = value
    rows[12][2] = "TOTAL HARTA"
    return pd.DataFrame(rows)


class _Workbook:
    sheet_names = ["SPT 2025", "SIMULASI I"]


def test_generic_importer_accepts_alias_headers_moved_columns_and_duplicate_block(tmp_path):
    source = tmp_path / "wp_lain.xlsx"
    source.write_bytes(b"placeholder")
    importer = GenericWorksheetWorkbookImporter()

    def fake_read_excel(_path, *, sheet_name, header, dtype):
        if sheet_name == "SPT 2025":
            return _annual_generic()
        return _simulasi_generic()

    with patch("core.worksheet_workbook_generic.pd.ExcelFile", return_value=_Workbook()), patch(
        "core.worksheet_workbook_generic.pd.read_excel", side_effect=fake_read_excel
    ), patch("core.worksheet_workbook_importer.pd.read_excel", side_effect=fake_read_excel):
        result = importer.parse(source)

    assert result.is_valid
    assert result.nama_wp == "CONTOH WP"
    assert result.npwp == "123456789012345"
    assert result.tahun_pajak == 2025
    assert len(result.bupot_rows) == 1
    assert result.bupot_rows[0].jenis == "BP21"
    assert result.bupot_rows[0].no_bupot == "GEN-001"
    assert result.bupot_rows[0].bruto == 10_000_000
    assert result.bupot_rows[0].pengurang == 2_000_000
    assert len(result.harta_rows) == 1
    assert result.harta_rows[0].kode_ct == "0104"
    assert result.harta_rows[0].kode_eform == "014"
    assert result.harta_rows[0].nama_harta == "Deposito"


def test_generic_year_sheet_detection():
    importer = GenericWorksheetWorkbookImporter()
    assert importer._find_year_sheet(["Data", "Kertas Kerja 2024", "SPT 2025"]) == "2025"
