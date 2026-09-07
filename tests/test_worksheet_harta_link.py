import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from ui.pages.import_coretax_page_view import ImportCoretaxPage
from ui.pages.worksheet_page import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaLink(unittest.TestCase):
    def setUp(self):
        self.import_page = ImportCoretaxPage()
        self.worksheet_page = WorksheetPage()
        self.import_page.harta_preview_changed.connect(
            self.worksheet_page.load_harta_preview
        )

    def tearDown(self):
        self.import_page.deleteLater()
        self.worksheet_page.deleteLater()

    @staticmethod
    def _result():
        row = WorksheetHartaRow(
            nomor=1,
            kode_eform="012",
            kode_ct="0102",
            nama_harta="Tabungan (Bank/Lembaga Keuangan)",
            nomor_akun_keterangan="116801005138508",
            atas_nama="EVY BACHTIAR",
            nama_bank="BRI",
            tahun_perolehan=2025,
            nilai_tahun_sebelumnya=0,
            nilai_tahun_berjalan=391742658,
        )
        return HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[row],
            current_year=2025,
        )

    def test_preview_signal_populates_worksheet_harta(self):
        result = self._result()

        self.import_page.harta_preview_changed.emit(result)

        self.assertIs(
            self.worksheet_page.harta_pipeline_result,
            result,
        )
        self.assertEqual(self.worksheet_page.harta_table.rowCount(), 1)
        self.assertEqual(
            self.worksheet_page.harta_table.item(0, 1).text(),
            "012",
        )
        self.assertEqual(
            self.worksheet_page.harta_table.item(0, 2).text(),
            "0102",
        )
        self.assertEqual(
            self.worksheet_page.harta_table.item(0, 9).text(),
            "391.742.658",
        )
        self.assertIn("Tahun 2025", self.worksheet_page.harta_status.text())

    def test_clear_signal_removes_stale_worksheet_data(self):
        self.import_page.harta_preview_changed.emit(self._result())
        self.assertEqual(self.worksheet_page.harta_table.rowCount(), 1)

        self.import_page.harta_preview_changed.emit(None)

        self.assertEqual(self.worksheet_page.harta_table.rowCount(), 0)
        self.assertIsNone(self.worksheet_page.harta_pipeline_result)
        self.assertIn(
            "Belum ada preview Harta",
            self.worksheet_page.harta_status.text(),
        )


if __name__ == "__main__":
    unittest.main()
