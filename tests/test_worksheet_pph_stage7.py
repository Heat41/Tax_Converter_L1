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
from ui.pages.worksheet_pph_stage7 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage7(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_stage7.db"
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
                    nomor_akun_keterangan="1",
                    atas_nama="EVY BACHTIAR",
                    nama_bank="BRI",
                    tahun_perolehan=2024,
                    nilai_tahun_sebelumnya=10_000_000,
                    nilai_tahun_berjalan=12_000_000,
                ),
                WorksheetHartaRow(
                    nomor=2,
                    kode_eform="034",
                    kode_ct="0305",
                    nama_harta="Obligasi",
                    nomor_akun_keterangan="2",
                    atas_nama="EVY BACHTIAR",
                    nama_bank="",
                    tahun_perolehan=2025,
                    nilai_tahun_sebelumnya=5_000_000,
                    nilai_tahun_berjalan=9_000_000,
                ),
            ],
            current_year=2025,
            npwp="6101015612710001",
            nama_wp="EVY BACHTIAR",
        )
        self.page.load_harta_preview(self.result)

    def tearDown(self):
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reconciliation_tab_and_harta_totals_are_available(self):
        tab_texts = [self.page.tabs.tabText(i) for i in range(self.page.tabs.count())]
        self.assertIn("Analisis Penghasilan vs Harta", tab_texts)
        self.assertEqual(self.page.harta_prev_value.text(), "15.000.000")
        self.assertEqual(self.page.harta_now_value.text(), "21.000.000")
        self.assertEqual(
            self.page.reconciliation_table.item(0, 3).text(),
            "6.000.000",
        )

    def test_signed_other_expense_is_allowed(self):
        item = self.page.reconciliation_table.item(3, 3)
        item.setText("-4.518.411")
        self.assertEqual(
            self.page._reconciliation_manual["pengeluaran_lain_lain"],
            -4_518_411,
        )

    def test_reconciliation_manual_state_persists(self):
        self.page._reconciliation_manual["utang_sebelumnya"] = 1_000_000
        self.page._reconciliation_manual["utang_berjalan"] = 2_000_000
        self.page._reconciliation_manual["pengeluaran_lain_lain"] = -500_000
        self.page._reconciliation_manual["margin_usaha"] = 0.2
        self.page._render_reconciliation()

        result = self.page.save_bupot_changes()
        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)

        second_page = WorksheetPage()
        second_page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        try:
            second_page.load_harta_preview(self.result)
            self.assertEqual(
                second_page._reconciliation_manual["utang_sebelumnya"],
                1_000_000,
            )
            self.assertEqual(
                second_page._reconciliation_manual["utang_berjalan"],
                2_000_000,
            )
            self.assertEqual(
                second_page._reconciliation_manual["pengeluaran_lain_lain"],
                -500_000,
            )
            self.assertEqual(
                second_page._reconciliation_manual["margin_usaha"],
                0.2,
            )
        finally:
            second_page.deleteLater()


if __name__ == "__main__":
    unittest.main()
