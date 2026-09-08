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

    def test_table_vertical_scrolling_remains_pixel_based(self):
        table = self.page.bupot_table
        self.assertEqual(
            table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            table.verticalScrollBarPolicy(),
            Qt.ScrollBarAsNeeded,
        )

    def test_pph_page_has_its_own_vertical_scroll_area(self):
        scroll = self.page.pph_scroll_area
        self.assertGreaterEqual(self.page.tabs.indexOf(scroll), 0)
        self.assertIs(scroll.widget(), self.page.pph_tab)
        self.assertTrue(scroll.widgetResizable())
        self.assertEqual(
            scroll.verticalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOn,
        )
        self.assertEqual(
            scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOff,
        )
        self.assertGreaterEqual(self.page.pph_tab.minimumHeight(), 650)
        self.assertEqual(scroll.verticalScrollBar().singleStep(), 24)


if __name__ == "__main__":
    unittest.main()
