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
from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage7Fix(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_stage7_fix.db"
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
                    tahun_perolehan=2025,
                    nilai_tahun_sebelumnya=0,
                    nilai_tahun_berjalan=16_268_223_888,
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

    def _fill_evy_bupot_total(self):
        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 1).setText("BP21")
        self.page.bupot_table.item(0, 2).setText("0123456789012345")
        self.page.bupot_table.item(0, 3).setText("TEST-EVY-2025")
        self.page.bupot_table.item(0, 4).setText("1.037.999.641")
        self.page.bupot_table.item(0, 5).setText("249.079.224")

    def test_linked_other_income_and_zakat_are_visible_in_summary(self):
        self._fill_evy_bupot_total()
        self.page._other_income_state["domestic_other_enabled"] = True
        self.page._other_income_state["domestic_other_dpp"] = 75_160_827
        self.page._other_income_state["zakat"] = 45_000_000
        self.page._sync_other_income_to_summary()

        self.assertEqual(
            self.page.pph_auto_values["penghasilan_neto_lainnya"].text(),
            "75.160.827",
        )
        self.assertEqual(
            self.page.pph_auto_values["pengurang_penghasilan_neto"].text(),
            "45.000.000",
        )
        self.assertEqual(
            self.page.pph_auto_values["penghasilan_neto_gabungan"].text(),
            "819.081.000",
        )

    def test_missing_previous_harta_requires_manual_baseline_instead_of_silent_zero(self):
        self.assertIn(
            "Baseline Harta tahun sebelumnya belum tersedia",
            self.page.reconciliation_status.text(),
        )
        self.assertFalse(self.page.harta_prev_value.isReadOnly())

        self.page.harta_prev_value.setText("15.009.974.357")
        self.page._on_harta_previous_baseline_finished()

        self.assertEqual(
            self.page._reconciliation_manual["harta_sebelumnya_override"],
            15_009_974_357,
        )
        self.assertEqual(self.page.harta_prev_value.text(), "15.009.974.357")
        self.assertIn(
            "Baseline Harta tahun sebelumnya: MANUAL",
            self.page.reconciliation_status.text(),
        )
        self.assertEqual(
            self.page.reconciliation_table.item(0, 3).text(),
            "1.258.249.531",
        )

    def test_manual_previous_harta_baseline_persists(self):
        self.page.harta_prev_value.setText("15.009.974.357")
        self.page._on_harta_previous_baseline_finished()
        result = self.page.save_bupot_changes()
        self.assertIsNotNone(result)

        second_page = WorksheetPage()
        second_page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        try:
            second_page.load_harta_preview(self.result)
            self.assertEqual(
                second_page._reconciliation_manual["harta_sebelumnya_override"],
                15_009_974_357,
            )
            self.assertEqual(
                second_page.harta_prev_value.text(),
                "15.009.974.357",
            )
        finally:
            second_page.deleteLater()


if __name__ == "__main__":
    unittest.main()
