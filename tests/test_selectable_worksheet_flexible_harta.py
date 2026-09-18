import pandas as pd

from core.selectable_worksheet_importer import SelectableWorksheetWorkbookImporter
from core.worksheet_workbook_importer import WorksheetWorkbookImportResult


def test_flexible_simulasi_harta_infers_columns_without_exact_header_aliases():
    rows = [[None] * 12 for _ in range(30)]

    # Header sengaja tidak memakai nama standar mapper.
    rows[8][1] = "Kode Aset"
    rows[8][2] = "Uraian"
    rows[8][6] = "Tahun Beli"
    rows[8][8] = "Saldo 2024"
    rows[8][9] = "Saldo 2025"

    rows[9][1] = "0104"
    rows[9][2] = "Deposito BRI"
    rows[9][6] = 2022
    rows[9][8] = 3000000000
    rows[9][9] = 3000000000

    rows[10][1] = "0305"
    rows[10][2] = "Obligasi"
    rows[10][6] = 2025
    rows[10][8] = 0
    rows[10][9] = 300000000

    rows[11][0] = "TOTAL HARTA"

    df = pd.DataFrame(rows)
    result = WorksheetWorkbookImportResult(
        source_path=None,
        npwp="6101015612710001",
        nama_wp="TEST",
        tahun_pajak=2025,
    )

    importer = SelectableWorksheetWorkbookImporter()
    importer._parse_harta(df, result)

    assert not result.errors
    assert len(result.harta_rows) == 2
    assert result.harta_rows[0].kode_ct == "0104"
    assert result.harta_rows[0].nama_harta == "Deposito BRI"
    assert result.harta_rows[0].tahun_perolehan == 2022
    assert result.harta_rows[0].nilai_tahun_sebelumnya == 3000000000
    assert result.harta_rows[0].nilai_tahun_berjalan == 3000000000
    assert result.harta_rows[1].kode_ct == "0305"


def test_unrecognized_simulasi_harta_is_warning_not_error():
    df = pd.DataFrame([["teks bebas"], ["tanpa tabel harta"]])
    result = WorksheetWorkbookImportResult(
        source_path=None,
        npwp="6101015612710001",
        nama_wp="TEST",
        tahun_pajak=2025,
    )

    importer = SelectableWorksheetWorkbookImporter()
    importer._parse_harta(df, result)

    assert not result.errors
    assert not result.harta_rows
    assert any(issue.code == "WKI_008" for issue in result.warnings)


def test_income_value_before_harta_table_is_not_imported_as_asset():
    rows = [[None] * 10 for _ in range(30)]

    rows[8][1] = "Kode Aset"
    rows[8][2] = "Uraian"
    rows[8][6] = "Tahun Beli"
    rows[8][8] = "Saldo 2024"
    rows[8][9] = "Saldo 2025"

    # Baris non-Harta: menyerupai bagian Jumlah Penghasilan dari Gaji karena
    # hanya memiliki nilai pada kolom tahun, tanpa KODE CT dan NAMA HARTA.
    rows[9][6] = 2025
    rows[9][9] = 337_160_131

    rows[10][1] = "0101"
    rows[10][2] = "KAS"
    rows[10][6] = 2024
    rows[10][8] = 10_000_000
    rows[10][9] = 10_000_000

    rows[11][1] = "0101"
    rows[11][2] = "BSI 7068-084-380"
    rows[11][6] = 2025
    rows[11][8] = 7_496_420
    rows[11][9] = 6_803_010

    rows[12][0] = "TOTAL HARTA"

    result = WorksheetWorkbookImportResult(
        source_path=None,
        npwp="6171042211890007",
        nama_wp="TEST",
        tahun_pajak=2025,
    )

    SelectableWorksheetWorkbookImporter()._parse_harta(
        pd.DataFrame(rows),
        result,
    )

    assert len(result.harta_rows) == 2
    assert result.harta_rows[0].nomor == 1
    assert result.harta_rows[0].kode_ct == "0101"
    assert result.harta_rows[0].nama_harta == "KAS"
    assert result.harta_rows[1].nama_harta == "BSI 7068-084-380"
