import sys
import unittest

from PySide6.QtWidgets import QApplication

from ui.pages.worksheet_pph_stage4 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage4(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_ptkp_status_and_pph_are_automatic(self):
        self.assertTrue(hasattr(self.page, "ptkp_status_combo"))
        self.assertTrue(self.page.pph_auto_values["ptkp"].isReadOnly())
        self.assertTrue(self.page.pph_auto_values["pph_terutang"].isReadOnly())

        self.page._status_ptkp = "TK/0"
        self.page._set_ptkp_combo("TK/0")
        self.page._pph_component_values["penghasilan_neto_lainnya"] = 54_001_000.0
        self.page._pph_component_values["pengurang_penghasilan_neto"] = 0.0
        self.page._pph_component_values["kredit_pajak"] = 84_519.0
        self.page._pph_component_values["pph25"] = 0.0

        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 4).setText("1.690.375")
        self.page.bupot_table.item(0, 5).setText("0")
        self.page._recalculate_pph_summary()

        self.assertEqual(self.page.pph_auto_values["ptkp"].text(), "54.000.000")
        self.assertEqual(self.page.pph_auto_values["pkp_simulasi"].text(), "1.691.000")
        self.assertEqual(self.page.pph_auto_values["pph_terutang"].text(), "84.550")
        self.assertEqual(self.page.pph_auto_values["kurang_lebih_bayar"].text(), "31")
        self.assertEqual(self.page.pph_rounded_value.text(), "0")

    def test_change_ptkp_status_updates_value(self):
        index = self.page.ptkp_status_combo.findData("K/1")
        self.page.ptkp_status_combo.setCurrentIndex(index)
        self.page._recalculate_pph_summary()

        self.assertEqual(self.page._status_ptkp, "K/1")
        self.assertEqual(self.page.pph_auto_values["ptkp"].text(), "63.000.000")


if __name__ == "__main__":
    unittest.main()
