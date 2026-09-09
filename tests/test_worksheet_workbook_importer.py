from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from config.database import init_database
from core.worksheet_pph_state import WorksheetPPhStateStore
from core.worksheet_state import WorksheetHartaStateStore
from core.worksheet_workbook_importer import WorksheetWorkbookImporter


def _annual_df():
    rows = [[None] * 10 for _ in range(84)]
    rows[0][0] = "KERTAS KERJA SPT TAHUNAN"
    rows[1][0] = "TAHUN 2025"
    rows[3][0], rows[3][1], rows[3][2] = "NAMA", ":", "EVY BACHTIAR"
    rows[4][0], rows[4][1], rows[4][2] = "NPWP", ":", "6101015612710001"

    headers = ["NO", "JENIS", "NPWP PEMBERI KERJA", "NO BUPOT", "BRUTO", "PENGURANG", "NETTO"]
    for offset, value in enumerate(headers, start=1):
        rows[7][offset] = value
    values = [1, "BP21", "0011050945093000", "250888969", 638298, 0, 638298]
    for offset, value in enumerate(values, start=1):
        rows[8][offset] = value
    rows[9][1] = "TOTAL"

    rows[36][0] = "PEREDARAN BRUTO UMKM"
    rows[37][1], rows[37][2], rows[37][4], rows[37][6] = "NO", "MASA", "BRUTO", "PPh Setor"
    for idx in range(12):
        rows[38 + idx][1] = idx + 1
        rows[38 + idx][2] = f"M{idx+1}"
    rows[38][4] = 100_000_000
    rows[38][6] = 250_000

    rows[52][0] = "PENGHASILAN LAINNYA"
    rows[53][1], rows[53][4], rows[53][5] = "Penghasilan Dalam Negeri Lainnya", "TIDAK", 0
    rows[54][1], rows[54][5], rows[54][6] = "Sewa atas Tanah dan/atau Bangunan", 0, 0
    rows[55][1], rows[55][5], rows[55][6] = "Honor", 75_160_827, 11_274_124
    rows[56][1], rows[56][5], rows[56][6] = "Penghasilan Final Lainnya", 679_500_000, 79_200_000
    rows[57][4], rows[57][5], rows[57][6] = "Deposito BRI", 90_000_000, 18_000_000
    rows[58][4], rows[58][5], rows[58][6] = "Obligasi", 567_000_000, 56_700_000
    rows[60][1], rows[60][5] = "Pekerjaan bebas", 0
    rows[61][1], rows[61][5] = "Prive", 0
    rows[62][1], rows[62][5], rows[62][7] = "Hibah / Warisan", 50_000_000, "dari Suami"
    rows[64][0], rows[64][4], rows[64][5] = "PENGURANG PENGHASILAN NETO", "Zakat", 45_000_000
    rows[67][1], rows[67][5] = "PTKP", "TK/0"
    rows[70][1], rows[70][5] = "PTKP", 54_000_000
    rows[77][1], rows[77][5] = "PPh21 Terutang", 150_976_000
    rows[78][1], rows[78][5] = "PPh21 sudah dipotong/ dipungut", 105_486_376
    rows[79][1], rows[79][5] = "Angsuran PPh Pasal 25", 0
    return pd.DataFrame(rows)


def _simulasi_df():
    rows = [[None] * 19 for _ in range(70)]
    rows[2][0], rows[2][2] = "NAMA :", "EVY BACHTIAR"
    rows[3][0], rows[3][2] = "NPWP :", "6101015612710001"
    headers = [
        "NO", "KODE EFORM", "KODE CT", "NAMA HARTA", "NOMOR AKUN / KETERANGAN",
        "ATAS NAMA", "NAMA BANK", "TH PEROLEHAN", "2024", "2025",
    ]
    for col, value in enumerate(headers):
        rows[19][col] = value
    rows[20][:10] = [1, None, "0104", "Deposito", "116801000285407", "EVY BACHTIAR", "BRI", 2022, 3_000_000_000, 3_000_000_000]
    rows[21][:10] = [2, None, "0305", "Obligasi", "1971197117", "EVY BACHTIAR", None, 2025, 0, 300_000_000]
    rows[22][0] = "TOTAL HARTA"

    rows[24][0] = "UTANG"
    rows[28][0], rows[28][8], rows[28][9] = "TOTAL", 100_000, 200_000
    rows[35][0], rows[35][1], rows[35][9] = "d", "Pengeluaran lain-lain", -4_518_411
    rows[36][0], rows[36][1], rows[36][9] = "e", "Kerugian (keuntungan) penjualan aset", 0
    rows[37][0], rows[37][1], rows[37][9] = "f", "Utang baru atas kredit", 0
    rows[38][0], rows[38][1], rows[38][9] = "g", "Harta baru dari kredit", 0
    rows[43][0], rows[43][9] = "Penambahan Penghasilan Bruto UMKM", 0
    rows[44][0], rows[44][9] = "Margin Usaha", 0
    return pd.DataFrame(rows)


class _ExcelFile:
    sheet_names = ["2025", "SIMULASI I", "REF"]


def test_parse_evy_style_workbook_and_persist():
    with tempfile.TemporaryDirectory() as temp:
        db_path = Path(temp) / "test.db"
        init_database(db_path)
        source = Path(temp) / "evy.xlsx"
        source.write_bytes(b"placeholder")

        importer = WorksheetWorkbookImporter(
            harta_store=WorksheetHartaStateStore(db_path),
            pph_store=WorksheetPPhStateStore(db_path),
        )

        def fake_read_excel(_path, *, sheet_name, header, dtype):
            return _annual_df() if sheet_name == "2025" else _simulasi_df()

        with patch("core.worksheet_workbook_importer.pd.ExcelFile", return_value=_ExcelFile()), patch(
            "core.worksheet_workbook_importer.pd.read_excel", side_effect=fake_read_excel
        ):
            result = importer.parse(source)

        assert result.is_valid
        assert result.npwp == "6101015612710001"
        assert result.nama_wp == "EVY BACHTIAR"
        assert result.tahun_pajak == 2025
        assert len(result.bupot_rows) == 1
        assert len(result.harta_rows) == 2
        assert result.harta_rows[0].kode_eform == "014"
        assert result.harta_rows[1].kode_eform == "034"
        assert result.pph_components["status_ptkp"] == "TK/0"
        assert result.pph_components["pengurang_penghasilan_neto"] == 45_000_000
        assert result.pph_components["pph_terutang"] == 150_976_000
        assert result.pph_components["kredit_pajak"] == 105_486_376
        assert result.pph_components["umkm_bruto_bulanan"][0] == 100_000_000
        assert result.pph_components["umkm_pph_setor_bulanan"][0] == 250_000
        assert result.pph_components["evy_other_income"]["honor_dpp"] == 75_160_827
        assert len(result.pph_components["evy_final_other_income_rows"]) == 2
        assert result.pph_components["evy_reconciliation"]["utang_berjalan"] == 200_000

        importer.persist(result)
        saved_pph = WorksheetPPhStateStore(db_path).load(result.npwp, 2025)
        assert saved_pph is not None
        assert len(saved_pph.bupot_rows) == 1
        assert saved_pph.components["status_ptkp"] == "TK/0"

        saved_harta = WorksheetHartaStateStore(db_path).load_matching(
            result.npwp, 2025, result.harta_rows
        )
        assert saved_harta is not None
        assert len(saved_harta.current_rows) == 2


def test_missing_simulasi_is_warning_not_identity_error():
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "annual.xlsx"
        source.write_bytes(b"placeholder")
        annual_only = type("AnnualOnly", (), {"sheet_names": ["2025"]})()
        importer = WorksheetWorkbookImporter()

        with patch("core.worksheet_workbook_importer.pd.ExcelFile", return_value=annual_only), patch(
            "core.worksheet_workbook_importer.pd.read_excel", return_value=_annual_df()
        ):
            result = importer.parse(source)

        assert result.is_valid
        assert not result.harta_rows
        assert any(issue.code == "WKI_101" for issue in result.warnings)
