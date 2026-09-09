import pandas as pd

from core.worksheet_workbook_importer import WorksheetWorkbookImportResult
from core.worksheet_workbook_importer_evy import WorksheetWorkbookImporter


def test_evy_duplicate_bupot_headers_choose_left_populated_block(tmp_path):
    rows = [[None] * 18 for _ in range(8)]
    rows[0][1:8] = ["NO", "JENIS", "NPWP PEMBERI KERJA", "NO BUPOT", "BRUTO", "PENGURANG", "NETTO"]
    rows[0][10:17] = ["NO", "JENIS", "NPWP PEMBERI KERJA", "NO BUPOT", "BRUTO", "PENGURANG", "NETTO"]
    rows[1][1:8] = [1, "BP21", "0011050945093000", "250888969", 638298, 0, 638298]
    rows[2][1:8] = [2, "BPA2", "0001159540702000", "2508L3ALJ", 551202899, 6000000, 545202899]
    rows[3][1] = "TOTAL"

    df = pd.DataFrame(rows)
    result = WorksheetWorkbookImportResult(source_path=tmp_path / "evy.xlsx")

    WorksheetWorkbookImporter()._parse_bupot(df, result)

    assert len(result.bupot_rows) == 2
    assert result.bupot_rows[0].jenis == "BP21"
    assert result.bupot_rows[0].no_bupot == "250888969"
    assert result.bupot_rows[1].jenis == "BPA2"
    assert result.bupot_rows[1].bruto == 551202899


def test_evy_left_block_totals_match_known_sample(tmp_path):
    rows = [[None] * 18 for _ in range(30)]
    headers = ["NO", "JENIS", "NPWP PEMBERI KERJA", "NO BUPOT", "BRUTO", "PENGURANG", "NETTO"]
    rows[0][1:8] = headers
    rows[0][10:17] = headers

    samples = [
        ("BP21", "0011050945093000", "250888969", 638298, 0),
        ("BPA2", "0001159540702000", "2508L3ALJ", 551202899, 6000000),
        ("BP21", "0001401850702000", "250AK0YI6", 29016417, 14508208),
    ]
    for idx, sample in enumerate(samples, start=1):
        jenis, npwp, no_bupot, bruto, pengurang = sample
        rows[idx][1:7] = [idx, jenis, npwp, no_bupot, bruto, pengurang]
    rows[len(samples) + 1][1] = "TOTAL"

    result = WorksheetWorkbookImportResult(source_path=tmp_path / "evy.xlsx")
    WorksheetWorkbookImporter()._parse_bupot(pd.DataFrame(rows), result)

    assert len(result.bupot_rows) == 3
    assert sum(row.bruto for row in result.bupot_rows) == 580857614
    assert sum(row.pengurang for row in result.bupot_rows) == 20508208
