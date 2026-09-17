import sys
import unittest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from core.three_sheet_worksheet_importer import ThreeSheetWorksheetWorkbookImporter
from ui.pages.input_data_page import InputDataPage
from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestThreeSheetWorksheetFlow(unittest.TestCase):
    def test_sheet_suggestions_detect_year_simulasi_and_revisi(self):
        importer = ThreeSheetWorksheetWorkbookImporter()
        year, simulasi, revisi = importer.suggested_sheets(
            ["2023", "SIMULASI I", "2024", "REVISI", "LAINNYA"]
        )
        self.assertEqual(year, "2024")
        self.assertEqual(simulasi, "SIMULASI I")
        self.assertEqual(revisi, "REVISI")

    def test_input_page_exposes_three_sheet_selectors(self):
        page = InputDataPage()
        try:
            self.assertIs(page.sheet_combo, page.year_sheet_combo)
            self.assertTrue(hasattr(page, "simulasi_sheet_combo"))
            self.assertTrue(hasattr(page, "revisi_sheet_combo"))
        finally:
            page.deleteLater()

    def test_pph_tab_title_follows_imported_year(self):
        page = WorksheetPage()
        try:
            result = SimpleNamespace(
                pipeline_result=None,
                revision_harta_rows=[],
                tahun_pajak=2024,
            )
            page.load_workbook_import_result(result)
            index = page.tabs.indexOf(page.pph_tab)
            self.assertGreaterEqual(index, 0)
            self.assertEqual(page.tabs.tabText(index), "Penghasilan & PPh 2024")
        finally:
            page.deleteLater()


if __name__ == "__main__":
    unittest.main()
