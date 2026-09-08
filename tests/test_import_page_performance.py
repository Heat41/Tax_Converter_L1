import sys
import unittest

from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView

from ui.pages.import_coretax_page_view import ImportCoretaxPage


app = QApplication.instance() or QApplication(sys.argv)


class TestImportPagePerformance(unittest.TestCase):
    def setUp(self):
        self.page = ImportCoretaxPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_preview_table_uses_pixel_scrolling(self):
        self.assertEqual(
            self.page.worksheet_table.horizontalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )
        self.assertEqual(
            self.page.worksheet_table.verticalScrollMode(),
            QAbstractItemView.ScrollPerPixel,
        )

    def test_preview_table_avoids_resize_to_contents(self):
        header = self.page.worksheet_table.horizontalHeader()
        for column in range(self.page.worksheet_table.columnCount()):
            self.assertEqual(
                header.sectionResizeMode(column),
                QHeaderView.Interactive,
            )

    def test_preview_table_uses_stable_geometry(self):
        self.assertFalse(self.page.worksheet_table.wordWrap())
        self.assertEqual(
            self.page.worksheet_table.verticalHeader().defaultSectionSize(),
            34,
        )
        self.assertEqual(self.page.worksheet_table.columnWidth(3), 230)
        self.assertEqual(self.page.worksheet_table.columnWidth(4), 235)

    def test_validation_and_page_scroll_are_optimized(self):
        header = self.page.table.horizontalHeader()
        self.assertEqual(header.sectionResizeMode(0), QHeaderView.Interactive)
        self.assertEqual(header.sectionResizeMode(4), QHeaderView.Stretch)
        self.assertEqual(self.page.table.verticalHeader().defaultSectionSize(), 36)
        self.assertEqual(self.page.scroll_area.verticalScrollBar().singleStep(), 26)


if __name__ == "__main__":
    unittest.main()
