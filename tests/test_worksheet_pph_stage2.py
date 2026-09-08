import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config.database import init_database
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_pph_state import WorksheetPPhStateStore
from core.worksheet_state import WorksheetHartaStateStore
from ui.pages.worksheet_pph_stage2 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage2(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_ui.db"
        init_database(self.db_path)
        self.pages = []
        self.result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[
                WorksheetHartaRow(
                    nomor=1,
                    kode_eform="012",
                    kode_ct="0102",
                    nama_harta="Tabungan",
                    nomor_akun_keterangan="TEST",
                    atas_nama="WP TEST",
                    nama_bank="BANK TEST",
                    tahun_perolehan=2025,
                    nilai_tahun_sebelumnya=0,
                    nilai_tahun_berjalan=1000000,
                )
            ],
            current_year=2025,
            npwp="0000000000000000",
            nama_wp="WP TEST",
        )

    def tearDown(self):
        for page in self.pages:
            page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _page(self):
        page = WorksheetPage()
        page.harta_state_store = WorksheetHartaStateStore(self.db_path)
        page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        page.load_harta_preview(self.result)
        self.pages.append(page)
        return page

    @staticmethod
    def _fill_valid_row(page, row=0, no_bupot="BUPOT-TEST-001"):
        page.bupot_table.item(row, 1).setText("1721-A1")
        page.bupot_table.item(row, 2).setText("000000000000000")
        page.bupot_table.item(row, 3).setText(no_bupot)
        page.bupot_table.item(row, 4).setText("1.500.000")
        page.bupot_table.item(row, 5).setText("500.000")

    def test_invalid_npwp_blocks_save_and_marks_cell(self):
        page = self._page()
        page._add_bupot_row()
        page.bupot_table.item(0, 1).setText("1721-A1")
        page.bupot_table.item(0, 2).setText("123")
        page.bupot_table.item(0, 3).setText("BUPOT-TEST-001")

        self.assertFalse(page.save_bupot_button.isEnabled())
        self.assertIn("15 atau 16 digit", page.bupot_table.item(0, 2).toolTip())
        self.assertIn("masalah validasi", page.pph_validation_status.text())

    def test_valid_bupot_saves_and_restores_from_database(self):
        first = self._page()
        first._add_bupot_row()
        self._fill_valid_row(first)

        self.assertTrue(first.save_bupot_button.isEnabled())
        result = first.save_bupot_changes()
        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)
        self.assertFalse(first.save_bupot_button.isEnabled())

        second = self._page()
        self.assertTrue(second._bupot_restored_from_db)
        self.assertEqual(second.bupot_table.rowCount(), 1)
        self.assertEqual(second.bupot_table.item(0, 1).text(), "1721-A1")
        self.assertEqual(second.bupot_table.item(0, 3).text(), "BUPOT-TEST-001")
        self.assertEqual(second.bupot_table.item(0, 6).text(), "1.000.000")

    def test_duplicate_no_bupot_is_rejected(self):
        page = self._page()
        page._add_bupot_row()
        self._fill_valid_row(page, 0, "BUPOT-DUPLIKAT")
        page._add_bupot_row()
        self._fill_valid_row(page, 1, "BUPOT-DUPLIKAT")

        self.assertFalse(page.save_bupot_button.isEnabled())
        self.assertIn("duplikat", page.bupot_table.item(0, 3).toolTip().lower())
        self.assertIn("duplikat", page.bupot_table.item(1, 3).toolTip().lower())

    def test_delete_all_rows_can_be_persisted(self):
        page = self._page()
        page._add_bupot_row()
        self._fill_valid_row(page)
        page.save_bupot_changes()

        page.bupot_table.selectRow(0)
        page._remove_bupot_row()
        self.assertEqual(page.bupot_table.rowCount(), 0)
        self.assertTrue(page.save_bupot_button.isEnabled())
        page.save_bupot_changes()

        restored = page.pph_state_store.load("0000000000000000", 2025)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.bupot_rows, [])


if __name__ == "__main__":
    unittest.main()
