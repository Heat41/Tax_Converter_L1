import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QAbstractItemView

from config.database import init_database
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_state import WorksheetHartaStateStore
from ui.pages.worksheet_page_view import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetAuditUI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "audit_ui.db"
        init_database(self.db_path)

        self.page = WorksheetPage()
        self.page.harta_state_store = WorksheetHartaStateStore(self.db_path)
        self.result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[
                WorksheetHartaRow(
                    nomor=1,
                    kode_eform="012",
                    kode_ct="0102",
                    nama_harta="Tabungan",
                    nomor_akun_keterangan="111",
                    atas_nama="WP",
                    nama_bank="BRI",
                    tahun_perolehan=2025,
                    nilai_tahun_sebelumnya=0,
                    nilai_tahun_berjalan=1000000,
                )
            ],
            current_year=2025,
            npwp="1234567890123456",
        )
        self.page.load_harta_preview(self.result)

    def tearDown(self):
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_toolbar_uses_two_rows_and_full_button_labels(self):
        grid = self.page.harta_action_grid
        original_row = grid.getItemPosition(grid.indexOf(self.page.original_button))[0]
        add_row = grid.getItemPosition(grid.indexOf(self.page.add_harta_button))[0]

        self.assertEqual(original_row, 0)
        self.assertEqual(add_row, 1)
        self.assertEqual(self.page.original_button.text(), "Original Import")
        self.assertEqual(self.page.current_button.text(), "Edited / Current")
        self.assertEqual(self.page.save_harta_button.text(), "Simpan Perubahan")
        self.assertGreaterEqual(self.page.save_harta_button.minimumWidth(), 135)

    def test_saved_edit_appears_in_audit_table(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.item(0, 5).setText("WP EDITED")
        result = self.page.save_harta_changes()

        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)
        self.assertEqual(self.page.audit_table.rowCount(), 1)
        self.assertEqual(self.page.audit_table.item(0, 1).text(), "EDIT")
        self.assertEqual(self.page.audit_table.item(0, 3).text(), "Atas Nama")
        self.assertEqual(self.page.audit_table.item(0, 4).text(), "WP")
        self.assertEqual(self.page.audit_table.item(0, 5).text(), "WP EDITED")
        self.assertIn("tersimpan di database", self.page.audit_summary.text())

    def test_audit_table_uses_pixel_scrolling(self):
        self.assertEqual(
            self.page.audit_table.horizontalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            self.page.audit_table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertFalse(self.page.audit_table.wordWrap())
        self.assertEqual(
            self.page.audit_table.verticalHeader().defaultSectionSize(),
            34,
        )


if __name__ == "__main__":
    unittest.main()
