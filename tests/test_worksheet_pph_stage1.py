import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView

from ui.pages.worksheet_pph_stage1 import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhStage1(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_add_bupot_row_initializes_editable_and_netto_cells(self):
        self.page._add_bupot_row()

        self.assertEqual(self.page.bupot_table.rowCount(), 1)
        self.assertEqual(self.page.bupot_table.item(0, 0).text(), "1")
        for column in range(1, 6):
            self.assertIsNotNone(self.page.bupot_table.item(0, column))
        netto = self.page.bupot_table.item(0, 6)
        self.assertIsNotNone(netto)
        self.assertEqual(netto.text(), "0")
        self.assertFalse(bool(netto.flags() & Qt.ItemIsEditable))

    def test_bruto_minus_pengurang_calculates_netto_automatically(self):
        self.page._add_bupot_row()
        self.page.bupot_table.item(0, 4).setText("1.500.000")
        self.page.bupot_table.item(0, 5).setText("500.000")

        self.assertEqual(self.page.bupot_table.item(0, 4).text(), "1.500.000")
        self.assertEqual(self.page.bupot_table.item(0, 5).text(), "500.000")
        self.assertEqual(self.page.bupot_table.item(0, 6).text(), "1.000.000")
        self.assertEqual(
            self.page.bupot_summary_values["jumlah_bupot"].text(), "1"
        )
        self.assertEqual(
            self.page.bupot_summary_values["total_bruto"].text(), "Rp 1.500.000"
        )
        self.assertEqual(
            self.page.bupot_summary_values["total_pengurang"].text(), "Rp 500.000"
        )
        self.assertEqual(
            self.page.bupot_summary_values["total_netto"].text(), "Rp 1.000.000"
        )


    def test_bupot_totals_are_persistent_fields_not_top_notification(self):
        self.assertTrue(hasattr(self.page, "bupot_summary_values"))
        self.assertFalse(self.page.pph_status.isVisible())
        self.assertEqual(
            set(self.page.bupot_summary_values),
            {
                "jumlah_bupot",
                "total_bruto",
                "total_pengurang",
                "total_netto",
                "total_pph",
            },
        )

    def test_bupot_table_uses_pixel_scrolling(self):
        self.assertEqual(
            self.page.bupot_table.horizontalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            self.page.bupot_table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertFalse(self.page.bupot_table.wordWrap())
        self.assertEqual(
            self.page.bupot_table.verticalHeader().defaultSectionSize(),
            34,
        )


if __name__ == "__main__":
    unittest.main()
