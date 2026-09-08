import sys
import unittest

from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView

from ui.pages.worksheet_page_view import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaPerformance(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_harta_table_uses_pixel_scrolling(self):
        self.assertEqual(
            self.page.harta_table.horizontalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            self.page.harta_table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )

    def test_harta_table_avoids_resize_to_contents(self):
        header = self.page.harta_table.horizontalHeader()
        for column in range(self.page.harta_table.columnCount()):
            self.assertEqual(
                header.sectionResizeMode(column),
                QHeaderView.Interactive,
            )

    def test_harta_table_uses_stable_geometry(self):
        self.assertFalse(self.page.harta_table.wordWrap())
        self.assertEqual(
            self.page.harta_table.verticalHeader().defaultSectionSize(),
            34,
        )
        self.assertEqual(self.page.harta_table.columnWidth(3), 230)
        self.assertEqual(self.page.harta_table.columnWidth(4), 235)


if __name__ == "__main__":
    unittest.main()
