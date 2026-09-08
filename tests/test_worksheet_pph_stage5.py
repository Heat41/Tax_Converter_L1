import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config.database import init_database
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_pph_state import WorksheetPPhStateStore
from ui.pages.worksheet_pph_stage5 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage5(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_stage5.db"
        init_database(self.db_path)
        self.page = WorksheetPage()
        self.page.pph_state_store = WorksheetPPhStateStore(self.db_path)
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
                    nilai_tahun_berjalan=1_000_000,
                )
            ],
            current_year=2025,
            npwp="6101015612710001",
            nama_wp="EVY BACHTIAR",
        )
        self.page.load_harta_preview(self.result)

    def tearDown(self):
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_umkm_table_matches_evy_structure(self):
        self.assertEqual(self.page.umkm_table.rowCount(), 13)
        self.assertEqual(self.page.umkm_table.item(0, 1).text(), "Januari")
        self.assertEqual(self.page.umkm_table.item(11, 1).text(), "Desember")
        self.assertEqual(self.page.umkm_table.item(12, 1).text(), "TOTAL")
        self.assertFalse(
            bool(self.page.umkm_table.item(0, 3).flags() & Qt.ItemIsEditable)
        )
        self.assertFalse(
            bool(self.page.umkm_table.item(0, 5).flags() & Qt.ItemIsEditable)
        )

    def test_umkm_threshold_formula_updates_ui(self):
        self.page.umkm_table.item(0, 2).setText("400.000.000")
        self.page.umkm_table.item(1, 2).setText("200.000.000")

        self.assertEqual(self.page.umkm_table.item(0, 3).text(), "0")
        self.assertEqual(self.page.umkm_table.item(1, 3).text(), "500.000")
        self.assertEqual(self.page.umkm_table.item(12, 2).text(), "600.000.000")
        self.assertEqual(self.page.umkm_table.item(12, 3).text(), "500.000")

    def test_pph_setor_produces_selisih(self):
        self.page.umkm_table.item(0, 2).setText("600.000.000")
        self.page.umkm_table.item(0, 4).setText("300.000")

        self.assertEqual(self.page.umkm_table.item(0, 3).text(), "500.000")
        self.assertEqual(self.page.umkm_table.item(0, 5).text(), "200.000")
        self.assertEqual(self.page.umkm_table.item(12, 5).text(), "200.000")

    def test_umkm_only_change_enables_save(self):
        self.page.umkm_table.item(0, 2).setText("100.000.000")
        self.assertTrue(self.page.save_bupot_button.isEnabled())
        self.assertTrue(self.page.save_pph_summary_button.isEnabled())

    def test_umkm_months_persist_with_worksheet_pph(self):
        self.page.umkm_table.item(0, 2).setText("400.000.000")
        self.page.umkm_table.item(1, 2).setText("200.000.000")
        self.page.umkm_table.item(1, 4).setText("500.000")
        save_result = self.page.save_bupot_changes()
        self.assertIsNotNone(save_result)
        self.assertTrue(save_result.persisted)

        second_page = WorksheetPage()
        second_page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        try:
            second_page.load_harta_preview(self.result)
            self.assertEqual(
                second_page.umkm_table.item(0, 2).text(), "400.000.000"
            )
            self.assertEqual(
                second_page.umkm_table.item(1, 2).text(), "200.000.000"
            )
            self.assertEqual(
                second_page.umkm_table.item(1, 3).text(), "500.000"
            )
            self.assertEqual(
                second_page.umkm_table.item(1, 4).text(), "500.000"
            )
            self.assertEqual(second_page.umkm_table.item(1, 5).text(), "0")
        finally:
            second_page.deleteLater()


if __name__ == "__main__":
    unittest.main()
