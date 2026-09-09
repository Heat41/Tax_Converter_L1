import sys

from PySide6.QtWidgets import QApplication

from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


def test_harta_table_reserves_ten_visible_rows():
    page = WorksheetPage()
    try:
        header = page.harta_table.horizontalHeader()
        header_height = max(header.height(), header.sizeHint().height())
        scrollbar_height = page.harta_table.horizontalScrollBar().sizeHint().height()
        minimum_expected = (
            header_height
            + (page.HARTA_VISIBLE_ROWS * page.HARTA_ROW_HEIGHT)
            + scrollbar_height
            + (page.harta_table.frameWidth() * 2)
        )

        assert page.HARTA_VISIBLE_ROWS == 10
        assert page.HARTA_ROW_HEIGHT == 34
        assert page.harta_table.minimumHeight() >= minimum_expected
    finally:
        page.deleteLater()
