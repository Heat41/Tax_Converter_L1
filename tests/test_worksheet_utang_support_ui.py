import sys
import unittest

from PySide6.QtWidgets import QApplication

from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetUtangSupportUi(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()
        self.page._utang_rows = [
            {
                "kode_utang": "102",
                "nama_pemberi_pinjaman": "BANK B",
                "alamat_pemberi_pinjaman": "JAKARTA",
                "tahun_pinjaman": 2025,
                "jumlah": 250_000_000,
            },
            {
                "kode_utang": "101",
                "nama_pemberi_pinjaman": "BANK A",
                "alamat_pemberi_pinjaman": "PONTIANAK",
                "tahun_pinjaman": 2023,
                "jumlah": 150_000_000,
            },
        ]
        self.page._render_utang_support_rows()

    def tearDown(self):
        self.page.deleteLater()

    def test_utang_table_is_read_only_and_has_expected_columns(self):
        self.assertEqual(self.page.utang_support_table.columnCount(), 6)
        self.assertEqual(
            [
                self.page.utang_support_table.horizontalHeaderItem(i).text()
                for i in range(6)
            ],
            [
                "NO",
                "KODE UTANG",
                "NAMA PEMBERI PINJAMAN",
                "ALAMAT PEMBERI PINJAMAN",
                "TAHUN PINJAMAN",
                "JUMLAH",
            ],
        )

    def test_utang_rows_sorted_by_year_and_totaled(self):
        table = self.page.utang_support_table
        self.assertEqual(table.rowCount(), 2)
        self.assertEqual(table.item(0, 1).text(), "101")
        self.assertEqual(table.item(0, 4).text(), "2023")
        self.assertEqual(table.item(1, 1).text(), "102")
        self.assertIn("400.000.000", self.page.utang_support_status.text())


if __name__ == "__main__":
    unittest.main()
