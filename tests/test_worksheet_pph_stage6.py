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
from ui.pages.worksheet_pph_stage6 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage6(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "pph_stage6.db"
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

    def _fill_evy_total_bupot(self):
        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 1).setText("BP21")
        self.page.bupot_table.item(0, 2).setText("0001401850702000")
        self.page.bupot_table.item(0, 3).setText("EVY-REFERENCE")
        self.page.bupot_table.item(0, 4).setText("1.037.999.641")
        self.page.bupot_table.item(0, 5).setText("249.079.224")

    def _set_zakat(self, value="45.000.000"):
        self.page.zakat_edit.setText(value)
        self.page._on_zakat_finished()

    def _set_evy_final_details(self):
        values = (
            ("Deposito BRI", "90.000.000"),
            ("Deposito BSI", "22.500.000"),
            ("Obligasi", "567.000.000"),
        )
        for row, (name, dpp) in enumerate(values):
            self.page.final_income_table.item(row, 0).setText(name)
            self.page.final_income_table.item(row, 1).setText(dpp)

    def test_evy_zakat_flows_into_progressive_summary(self):
        self._fill_evy_total_bupot()
        self._set_zakat()

        self.assertEqual(
            self.page.pph_auto_values["total_netto_bupot"].text(),
            "788.920.417",
        )
        self.assertEqual(
            self.page.pph_auto_values["penghasilan_neto_gabungan"].text(),
            "743.920.000",
        )
        self.assertEqual(
            self.page.pph_auto_values["pkp_simulasi"].text(),
            "689.920.000",
        )
        self.assertEqual(
            self.page.pph_auto_values["pph_terutang"].text(),
            "150.976.000",
        )

    def test_evy_final_income_and_zakat_persist(self):
        self._fill_evy_total_bupot()
        self._set_zakat()
        self._set_evy_final_details()

        self.assertEqual(
            self.page.final_income_status.text(),
            "Subtotal Penghasilan Final Lainnya • DPP Rp 679.500.000 • PPh Rp 79.200.000",
        )

        result = self.page.save_bupot_changes()
        self.assertIsNotNone(result)
        self.assertTrue(result.persisted)

        second_page = WorksheetPage()
        second_page.pph_state_store = WorksheetPPhStateStore(self.db_path)
        try:
            second_page.load_harta_preview(self.result)
            self.assertEqual(second_page.zakat_edit.text(), "45.000.000")
            self.assertEqual(
                second_page.final_income_table.item(0, 0).text(),
                "Deposito BRI",
            )
            self.assertEqual(
                second_page.final_income_table.item(2, 1).text(),
                "567.000.000",
            )
            self.assertEqual(
                second_page.final_income_status.text(),
                "Subtotal Penghasilan Final Lainnya • DPP Rp 679.500.000 • PPh Rp 79.200.000",
            )
        finally:
            second_page.deleteLater()


if __name__ == "__main__":
    unittest.main()
