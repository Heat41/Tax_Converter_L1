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
from ui.pages.worksheet_pph_stage3 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage3(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_stage3.db"
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
                    nilai_tahun_berjalan=1000000,
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

    def _fill_valid_bupot(self):
        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 1).setText("PPh 21")
        self.page.bupot_table.item(0, 2).setText("0123456789012345")
        self.page.bupot_table.item(0, 3).setText("BUPOT-2025-0001")
        self.page.bupot_table.item(0, 4).setText("120.000.000")
        self.page.bupot_table.item(0, 5).setText("6.000.000")

    def _set_component(self, key, value):
        edit = self.page.pph_component_edits[key]
        edit.setText(value)
        self.page._on_pph_component_finished(key)

    def test_bupot_netto_flows_into_annual_summary(self):
        self._fill_valid_bupot()
        self.assertEqual(
            self.page.pph_auto_values["total_netto_bupot"].text(),
            "114.000.000",
        )

    def test_basic_annual_summary_calculation(self):
        self._fill_valid_bupot()
        self._set_component("penghasilan_neto_lainnya", "10.000.000")
        self._set_component("pengurang_penghasilan_neto", "4.000.000")
        self._set_component("ptkp", "54.000.000")
        self._set_component("pph_terutang", "12.000.000")
        self._set_component("kredit_pajak", "8.000.000")
        self._set_component("pph25", "1.000.000")

        self.assertEqual(
            self.page.pph_auto_values["penghasilan_neto_gabungan"].text(),
            "120.000.000",
        )
        self.assertEqual(
            self.page.pph_auto_values["pkp_simulasi"].text(),
            "66.000.000",
        )
        self.assertEqual(
            self.page.pph_auto_values["kurang_lebih_bayar"].text(),
            "3.000.000",
        )

    def test_components_persist_with_bupot(self):
        self._fill_valid_bupot()
        self._set_component("ptkp", "54.000.000")
        self._set_component("pph_terutang", "12.000.000")
        result = self.page.save_bupot_changes()
        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)

        second_page = WorksheetPage()
        second_page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        try:
            second_page.load_harta_preview(self.result)
            self.assertEqual(second_page.bupot_table.rowCount(), 1)
            self.assertEqual(
                second_page.pph_component_edits["ptkp"].text(),
                "54.000.000",
            )
            self.assertEqual(
                second_page.pph_component_edits["pph_terutang"].text(),
                "12.000.000",
            )
            self.assertEqual(
                second_page.pph_auto_values["total_netto_bupot"].text(),
                "114.000.000",
            )
        finally:
            second_page.deleteLater()

    def test_component_only_change_enables_save(self):
        self._set_component("ptkp", "54.000.000")
        self.assertTrue(self.page.save_bupot_button.isEnabled())
        self.assertTrue(self.page.save_pph_summary_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
