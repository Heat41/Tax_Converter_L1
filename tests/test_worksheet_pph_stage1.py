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
        self.assertIn("Total Netto Rp 1.000.000", self.page.pph_status.text())

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
