import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.pages.import_coretax_page import ImportCoretaxPage

# Ensure single QApplication instance for widget testing
app = QApplication.instance() or QApplication(sys.argv)


class TestImportCoretaxPage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.page = ImportCoretaxPage()
        self.page.show()

    def tearDown(self):
        self.page.hide()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.page.deleteLater()

    def test_initial_state(self):
        """Memastikan state awal UI sebelum file dipilih."""
        self.assertIsNone(self.page.selected_file)
        self.assertIsNone(self.page.current_file_info)
        self.assertFalse(self.page.import_button.isEnabled())
        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertEqual(self.page.table.columnCount(), 0)
        self.assertTrue(self.page.sheet_container.isHidden())
        self.assertEqual(self.page.file_label.text(), "Belum ada file yang dipilih")

    @patch.object(QMessageBox, "information")
    def test_load_file_and_import_button_trigger_xlsx(self, mock_info):
        """Menguji flow penuh UI: memilih file XLSX, menekan tombol Impor, dan melihat hasil preview."""
        file_path = os.path.join(self.temp_dir, "test_harta.xlsx")
        df = pd.DataFrame({
            "Kode Harta": ["01001", "02005"],
            "Nama Harta": ["Tabungan BCA", "Mobil Toyota"],
            "Nilai": ["150000000", "300000000"],
            "Keterangan": ["Rekening aktif", "Kondisi baik"],
        })
        df.to_excel(file_path, sheet_name="DataHarta", index=False)

        # 1. UI memuat file (seperti aksi user setelah QFileDialog)
        self.page.load_file(file_path)

        self.assertEqual(self.page.selected_file, Path(file_path).resolve())
        self.assertIsNotNone(self.page.current_file_info)
        self.assertTrue(self.page.import_button.isEnabled())
        self.assertIn("test_harta.xlsx", self.page.file_label.text())

        # 2. User mengklik tombol 'Validasi & Impor'
        self.page.import_button.click()

        # 3. Verifikasi dialog sukses muncul
        self.assertTrue(mock_info.called)

        # 4. Verifikasi isi tabel preview hasil render UI
        self.assertEqual(self.page.table.rowCount(), 2)
        self.assertEqual(self.page.table.columnCount(), 4)

        headers = [
            self.page.table.horizontalHeaderItem(i).text()
            for i in range(self.page.table.columnCount())
        ]
        self.assertEqual(headers, ["Kode Harta", "Nama Harta", "Nilai", "Keterangan"])

        # Verifikasi data baris & preservasi leading zeros
        self.assertEqual(self.page.table.item(0, 0).text(), "01001")
        self.assertEqual(self.page.table.item(0, 1).text(), "Tabungan BCA")
        self.assertEqual(self.page.table.item(0, 2).text(), "150000000")
        self.assertEqual(self.page.table.item(1, 0).text(), "02005")
        self.assertEqual(self.page.table.item(1, 1).text(), "Mobil Toyota")

        # Verifikasi info badge & progress
        self.assertEqual(self.page.preview_info_label.text(), "2 baris • 4 kolom")
        self.assertEqual(self.page.progress.value(), 100)

    @patch.object(QMessageBox, "information")
    def test_load_file_and_import_multi_sheet_switch(self, mock_info):
        """Menguji flow UI jika file Excel memiliki beberapa sheet."""
        file_path = os.path.join(self.temp_dir, "multi_tab.xlsx")
        df1 = pd.DataFrame({"Kas": ["1000", "2000"]})
        df2 = pd.DataFrame({
            "Kode Piutang": ["P01", "P02"],
            "Debitur": ["PT Alfa", "PT Beta"],
            "Nilai": ["50000000", "75000000"]
        })

        with pd.ExcelWriter(file_path) as writer:
            df1.to_excel(writer, sheet_name="KasBank", index=False)
            df2.to_excel(writer, sheet_name="DaftarPiutang", index=False)

        # 1. Muat file
        self.page.load_file(file_path)

        # 2. Verifikasi sheet container muncul
        self.assertTrue(self.page.sheet_container.isVisible())
        self.assertEqual(self.page.sheet_combo.count(), 2)
        self.assertEqual(self.page.sheet_combo.itemText(0), "KasBank")
        self.assertEqual(self.page.sheet_combo.itemText(1), "DaftarPiutang")

        # 3. User memilih sheet kedua
        self.page.sheet_combo.setCurrentText("DaftarPiutang")

        # 4. User klik Impor
        self.page.import_button.click()

        # 5. Verifikasi preview membaca sheet yang dipilih
        self.assertEqual(self.page.table.rowCount(), 2)
        self.assertEqual(self.page.table.columnCount(), 3)
        self.assertEqual(self.page.table.horizontalHeaderItem(0).text(), "Kode Piutang")
        self.assertEqual(self.page.table.horizontalHeaderItem(1).text(), "Debitur")
        self.assertEqual(self.page.table.item(0, 1).text(), "PT Alfa")

    @patch.object(QMessageBox, "information")
    def test_load_file_csv_and_import(self, mock_info):
        """Menguji flow UI saat memilih file CSV dengan leading zero."""
        file_path = os.path.join(self.temp_dir, "wajib_pajak.csv")
        csv_content = (
            "NPWP,Nama WP,Kode Harta,Nilai\n"
            "001234567890000,PT Maju Terus,01001,500000000\n"
            "009876543210000,CV Berkah,02005,250000000\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        self.page.load_file(file_path)
        self.assertFalse(self.page.sheet_container.isVisible())
        self.assertTrue(self.page.import_button.isEnabled())

        self.page.import_button.click()

        self.assertEqual(self.page.table.rowCount(), 2)
        self.assertEqual(self.page.table.columnCount(), 4)
        self.assertEqual(self.page.table.item(0, 0).text(), "001234567890000")
        self.assertEqual(self.page.table.item(0, 2).text(), "01001")
        self.assertEqual(self.page.table.item(1, 0).text(), "009876543210000")
        self.assertEqual(self.page.table.item(1, 2).text(), "02005")

    @patch.object(QMessageBox, "warning")
    def test_load_unsupported_file_format(self, mock_warning):
        """Menguji UI jika user memilih format file yang tidak didukung."""
        file_path = os.path.join(self.temp_dir, "dokumen.txt")
        with open(file_path, "w") as f:
            f.write("test content")

        self.page.load_file(file_path)

        self.assertTrue(mock_warning.called)
        self.assertIsNone(self.page.selected_file)
        self.assertFalse(self.page.import_button.isEnabled())
        self.assertEqual(self.page.file_label.text(), "File tidak valid atau tidak dapat dibuka.")

    @patch.object(QMessageBox, "warning")
    def test_load_empty_file(self, mock_warning):
        """Menguji UI jika user memilih file kosong (0 byte)."""
        file_path = os.path.join(self.temp_dir, "empty.xlsx")
        with open(file_path, "wb") as f:
            pass

        self.page.load_file(file_path)

        self.assertTrue(mock_warning.called)
        self.assertIsNone(self.page.selected_file)
        self.assertFalse(self.page.import_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
