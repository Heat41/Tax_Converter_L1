import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from ui.pages.worksheet_page_view import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaView(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()
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
        result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[row],
            current_year=2025,
        )
        self.page.load_harta_preview(result)

    def tearDown(self):
        self.page.deleteLater()

    def test_status_mode_is_bold(self):
        self.assertTrue(self.page.harta_status.font().bold())

    def test_current_mode_shows_notice(self):
        self.page._show_harta_mode("current")
        self.assertTrue(self.page.harta_notice.isVisible())
        self.assertIn("EDITED / CURRENT", self.page.harta_notice.text())

    def test_direct_reset_shows_success_notice(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.item(0, 3).setText("Koreksi")
        self.page.reset_harta_to_import()
        self.assertIn("berhasil dikembalikan", self.page.harta_notice.text())


if __name__ == "__main__":
    unittest.main()
