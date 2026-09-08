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
from core.worksheet_state import WorksheetHartaStateStore
from ui.pages.worksheet_page_view import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "ui_state.db"
        init_database(self.db_path)
        self.store = WorksheetHartaStateStore(self.db_path)
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
        self.pages = []

    def tearDown(self):
        for page in self.pages:
            page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _page(self):
        page = WorksheetPage()
        page.harta_state_store = self.store
        self.pages.append(page)
        return page

    def test_save_persists_to_database(self):
        page = self._page()
        page.load_harta_preview(self.result)
        page._show_harta_mode("current")
        page.harta_table.item(0, 5).setText("WP EDITED")

        result = page.save_harta_changes()

        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)
        self.assertEqual(result.edit_count, 1)
        self.assertFalse(page.save_harta_button.isEnabled())
        self.assertIn("TERSIMPAN KE DATABASE", page.harta_status.text())
        self.assertIn("tersimpan ke database", page.harta_notice.text().lower())

    def test_same_original_restores_saved_current(self):
        first = self._page()
        first.load_harta_preview(self.result)
        first._show_harta_mode("current")
        first.harta_table.item(0, 5).setText("WP EDITED")
        first.save_harta_changes()

        second = self._page()
        second.load_harta_preview(self.result)

        self.assertTrue(second.harta_restored_from_db)
        self.assertEqual(second.harta_current_rows[0].atas_nama, "WP EDITED")
        second._show_harta_mode("current")
        self.assertEqual(second.harta_table.item(0, 5).text(), "WP EDITED")
        self.assertFalse(second.save_harta_button.isEnabled())
        self.assertIn("database", second.harta_status.text().lower())


if __name__ == "__main__":
    unittest.main()
