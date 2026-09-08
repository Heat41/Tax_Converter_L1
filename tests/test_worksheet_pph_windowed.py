import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QAbstractScrollArea

from ui.pages.worksheet_pph_windowed import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetPPhWindowed(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_horizontal_scrollbar_is_available_in_windowed_mode(self):
        table = self.page.bupot_table
        self.assertEqual(
            table.horizontalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOn,
        )
        self.assertEqual(
            table.horizontalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            table.sizeAdjustPolicy(),
            QAbstractScrollArea.AdjustIgnored,
        )
        self.assertEqual(table.minimumWidth(), 0)

    def test_vertical_scrolling_remains_pixel_based(self):
        table = self.page.bupot_table
        self.assertEqual(
            table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            table.verticalScrollBarPolicy(),
            Qt.ScrollBarAsNeeded,
        )


if __name__ == "__main__":
    unittest.main()
