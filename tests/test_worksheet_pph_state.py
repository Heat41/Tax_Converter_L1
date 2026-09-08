import shutil
import tempfile
import unittest
from pathlib import Path

from config.database import get_db_connection, init_database
from core.worksheet_pph_state import WorksheetBupotRow, WorksheetPPhStateStore


class TestWorksheetPPhState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_state.db"
        init_database(self.db_path)
        self.store = WorksheetPPhStateStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_schema_creates_worksheet_pph_states(self):
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='worksheet_pph_states'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()

    def test_save_and_load_bupot_rows(self):
        rows = [
            WorksheetBupotRow(
                jenis="1721-A1",
                npwp_pemberi_kerja="00.000.000.0-000.000",
                no_bupot="BUPOT-TEST-001",
                bruto=1500000,
                pengurang=500000,
            )
        ]
        result = self.store.save(
            npwp="0000000000000000",
            tahun_pajak=2025,
            bupot_rows=rows,
        )

        self.assertTrue(result.persisted)
        self.assertEqual(result.row_count, 1)

        restored = self.store.load("0000000000000000", 2025)
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored.bupot_rows), 1)
        self.assertEqual(restored.bupot_rows[0].jenis, "1721-A1")
        self.assertEqual(restored.bupot_rows[0].npwp_pemberi_kerja, "000000000000000")
        self.assertEqual(restored.bupot_rows[0].netto, 1000000)

    def test_save_overwrites_same_wp_year_without_duplicate_state(self):
        self.store.save(
            npwp="0000000000000000",
            tahun_pajak=2025,
            bupot_rows=[WorksheetBupotRow(jenis="A", npwp_pemberi_kerja="000000000000000", no_bupot="TEST-1")],
        )
        self.store.save(
            npwp="0000000000000000",
            tahun_pajak=2025,
            bupot_rows=[WorksheetBupotRow(jenis="B", npwp_pemberi_kerja="000000000000000", no_bupot="TEST-2")],
        )

        restored = self.store.load("0000000000000000", 2025)
        self.assertEqual(len(restored.bupot_rows), 1)
        self.assertEqual(restored.bupot_rows[0].jenis, "B")
        self.assertEqual(restored.bupot_rows[0].no_bupot, "TEST-2")

        conn = get_db_connection(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM worksheet_pph_states").fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
