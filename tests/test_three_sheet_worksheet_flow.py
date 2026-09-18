import sys
import unittest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
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


    def test_sheet_status_includes_year_and_updates_from_manual_selection(self):
        page = InputDataPage()
        try:
            page.worksheet_path = __import__("pathlib").Path("dummy.xlsx")
            page.year_sheet_combo.addItems(["2024", "2025"])
            page.simulasi_sheet_combo.addItems(["SIMULASI I"])
            page.revisi_sheet_combo.addItems(["", "REVISI"])

            page.year_sheet_combo.setCurrentText("2025")
            page.simulasi_sheet_combo.setCurrentText("SIMULASI I")
            page.revisi_sheet_combo.setCurrentText("")

            page._refresh_sheet_selector_status()

            text = page.sheet_selector_status.text()
            self.assertIn("Sheet Tahun: ✓ 2025", text)
            self.assertIn("SIMULASI I: ✓ ditemukan", text)
            self.assertIn("REVISI: tidak ditemukan / opsional", text)
            self.assertTrue(page.import_worksheet_button.isEnabled())
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
            titles = [
                page.tabs.tabText(index)
                for index in range(page.tabs.count())
            ]
            self.assertIn("Penghasilan & PPh 2024", titles)
        finally:
            page.deleteLater()

    def test_harta_header_row_is_not_asset(self):
        importer = ThreeSheetWorksheetWorkbookImporter()
        header = WorksheetHartaRow(
            nomor=1,
            kode_eform="KODE EFORM",
            kode_ct="KODE CT",
            nama_harta="NAMA HARTA",
            nomor_akun_keterangan="NOMOR AKUN / KETERANGAN",
            atas_nama="ATAS NAMA",
            nama_bank="NAMA BANK",
            tahun_perolehan=2025,
            nilai_tahun_sebelumnya=0,
            nilai_tahun_berjalan=0,
        )
        real_asset = WorksheetHartaRow(
            nomor=2,
            kode_eform="011",
            kode_ct="0101",
            nama_harta="Kas",
            nomor_akun_keterangan="",
            atas_nama="VIKTOR",
            nama_bank="",
            tahun_perolehan=2024,
            nilai_tahun_sebelumnya=1000000,
            nilai_tahun_berjalan=1500000,
        )

        self.assertTrue(importer._is_harta_header_row(header))
        self.assertFalse(importer._is_harta_header_row(real_asset))


if __name__ == "__main__":
    unittest.main()
