from pathlib import Path
import tempfile

from config.database import init_database
from core.worksheet_pph_state import WorksheetBupotRow, WorksheetPPhStateStore
from core.worksheet_state import WorksheetHartaStateStore
from core.worksheet_workbook_importer import (
    WorksheetWorkbookImporter,
    WorksheetWorkbookImportResult,
)


def _result(path: Path):
    return WorksheetWorkbookImportResult(
        source_path=path,
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
        bupot_rows=[
            WorksheetBupotRow(
                jenis="BP21",
                npwp_pemberi_kerja="0011050945093000",
                no_bupot="NEW-BUPOT",
                bruto=100_000_000,
                pengurang=5_000_000,
            )
        ],
        pph_components={"status_ptkp": "TK/0"},
    )


def test_include_bupot_true_imports_rows():
    with tempfile.TemporaryDirectory() as temp:
        db_path = Path(temp) / "test.db"
        init_database(db_path)
        pph_store = WorksheetPPhStateStore(db_path)
        importer = WorksheetWorkbookImporter(
            harta_store=WorksheetHartaStateStore(db_path),
            pph_store=pph_store,
        )

        result = _result(Path(temp) / "worksheet.xlsx")
        importer.persist(result, include_bupot=True)

        saved = pph_store.load(result.npwp, 2025)
        assert saved is not None
        assert [row.no_bupot for row in saved.bupot_rows] == ["NEW-BUPOT"]


def test_include_bupot_false_preserves_existing_rows():
    with tempfile.TemporaryDirectory() as temp:
        db_path = Path(temp) / "test.db"
        init_database(db_path)
        pph_store = WorksheetPPhStateStore(db_path)
        pph_store.save(
            npwp="6101015612710001",
            tahun_pajak=2025,
            bupot_rows=[
                WorksheetBupotRow(
                    jenis="BP21",
                    npwp_pemberi_kerja="0011050945093000",
                    no_bupot="OLD-BUPOT",
                    bruto=50_000_000,
                    pengurang=0,
                )
            ],
            components={"status_ptkp": "TK/0"},
        )
        importer = WorksheetWorkbookImporter(
            harta_store=WorksheetHartaStateStore(db_path),
            pph_store=pph_store,
        )

        result = _result(Path(temp) / "worksheet.xlsx")
        importer.persist(result, include_bupot=False)

        saved = pph_store.load(result.npwp, 2025)
        assert saved is not None
        assert [row.no_bupot for row in saved.bupot_rows] == ["OLD-BUPOT"]
        assert saved.components["status_ptkp"] == "TK/0"
