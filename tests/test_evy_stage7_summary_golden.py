import sys
import unittest

from PySide6.QtWidgets import QApplication

from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestEvyStage7SummaryGolden(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_evy_honor_does_not_become_domestic_other_income(self):
        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 1).setText("BP21")
        self.page.bupot_table.item(0, 2).setText("0123456789012345")
        self.page.bupot_table.item(0, 3).setText("TEST-EVY-2025")
        self.page.bupot_table.item(0, 4).setText("1.037.999.641")
        self.page.bupot_table.item(0, 5).setText("249.079.224")

        self.page._other_income_state["domestic_other_enabled"] = False
        self.page._other_income_state["domestic_other_dpp"] = 0.0
        self.page._other_income_state["honor_dpp"] = 75_160_827.0
        self.page._other_income_state["honor_pph"] = 11_274_124.0
        self.page._other_income_state["zakat"] = 45_000_000.0
        self.page._sync_other_income_to_summary()

        self.assertEqual(
            self.page.pph_auto_values["penghasilan_neto_lainnya"].text(),
            "0",
        )
        self.assertEqual(
            self.page.pph_auto_values["pengurang_penghasilan_neto"].text(),
            "45.000.000",
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


if __name__ == "__main__":
    unittest.main()
