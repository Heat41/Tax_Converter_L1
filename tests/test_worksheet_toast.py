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
from ui.pages.worksheet_notifications import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetToast(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "toast.db"
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
                    atas_nama="EVY BACHTIAR",
                    nama_bank="BRI",
                    tahun_perolehan=2025,
                    nilai_tahun_sebelumnya=0,
                    nilai_tahun_berjalan=1000000,
                )
            ],
            current_year=2025,
            npwp="6101015612710001",
            nama_wp="EVY BACHTIAR",
        )

    def tearDown(self):
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preview_shows_non_blocking_toast(self):
        self.page.load_harta_preview(self.result)

        self.assertFalse(self.page.toast_notification.isHidden())
        self.assertIn("Preview Harta", self.page.toast_notification.message_label.text())
        self.assertTrue(self.page.toast_notification._timer.isActive())

    def test_database_save_shows_success_toast(self):
        self.page.load_harta_preview(self.result)
        self.page._show_harta_mode("current")
        self.page.harta_table.item(0, 9).setText("2.000.000")

        result = self.page.save_harta_changes()

        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)
        self.assertIn("tersimpan ke database", self.page.toast_notification.message_label.text())


if __name__ == "__main__":
    unittest.main()
