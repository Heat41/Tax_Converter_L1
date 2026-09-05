import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.pages.import_coretax_page import ImportCoretaxPage


# Pastikan hanya ada satu QApplication
app = QApplication.instance() or QApplication(sys.argv)


class TestImportCoretaxPage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.page = ImportCoretaxPage()
        self.page.show()

    def tearDown(self):
        self.page.hide()
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initial_state(self):
        """Memastikan state awal UI Stage 3B."""
        self.assertEqual(self.page.selected_files, [])
        self.assertIsNone(self.page.last_result)

        self.assertFalse(self.page.validate_button.isEnabled())

        self.assertEqual(
            self.page.file_label.text(),
            "Belum ada file yang dipilih",
        )

        self.assertEqual(
            self.page.status_label.text(),
            "Menunggu sumber data...",
        )

        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertEqual(self.page.table.columnCount(), 5)

        headers = [
            self.page.table.horizontalHeaderItem(i).text()
            for i in range(self.page.table.columnCount())
        ]

        self.assertEqual(
            headers,
            ["Kategori", "File", "Status", "Baris", "Pesan"],
        )

        self.assertEqual(
            self.page.count_label.text(),
            "0 / 6 kategori",
        )

    def test_set_single_file(self):
        """Satu file kategori dapat dipilih."""
        file_path = Path(self.temp_dir) / (
            "PIT L1 Harta Kas Setara Kas 250918.xlsx"
        )

        file_path.touch()

        self.page.set_files([file_path])

        self.assertEqual(len(self.page.selected_files), 1)
        self.assertEqual(
            self.page.selected_files[0],
            file_path.resolve(),
        )

        self.assertTrue(self.page.validate_button.isEnabled())
        self.assertIn(
            file_path.name,
            self.page.file_label.text(),
        )

    def test_set_multiple_files(self):
        """Beberapa file dapat dipilih sekaligus."""
        files = [
            Path(self.temp_dir) / "PIT L1 Harta Kas Setara Kas 250918.xlsx",
            Path(self.temp_dir) / "PIT L1 Harta Piutang 250918.xlsx",
            Path(self.temp_dir) / "PIT L1 Harta Investasi 250918.xlsx",
        ]

        for path in files:
            path.touch()

        self.page.set_files(files)

        self.assertEqual(len(self.page.selected_files), 3)
        self.assertTrue(self.page.validate_button.isEnabled())

        for path in files:
            self.assertIn(path.name, self.page.file_label.text())

    def test_set_files_removes_duplicates(self):
        """File yang sama tidak boleh tersimpan dua kali."""
        file_path = Path(self.temp_dir) / (
            "PIT L1 Harta Kas Setara Kas 250918.xlsx"
        )

        file_path.touch()

        self.page.set_files([
            file_path,
            file_path,
            file_path,
        ])

        self.assertEqual(len(self.page.selected_files), 1)

    def test_clear_selection(self):
        """Bersihkan mengembalikan UI ke kondisi awal."""
        file_path = Path(self.temp_dir) / (
            "PIT L1 Harta Kas Setara Kas 250918.xlsx"
        )

        file_path.touch()

        self.page.set_files([file_path])
        self.assertTrue(self.page.validate_button.isEnabled())

        self.page.clear_selection()

        self.assertEqual(self.page.selected_files, [])
        self.assertIsNone(self.page.last_result)

        self.assertFalse(self.page.validate_button.isEnabled())

        self.assertEqual(
            self.page.file_label.text(),
            "Belum ada file yang dipilih",
        )

        self.assertEqual(
            self.page.status_label.text(),
            "Menunggu sumber data...",
        )

        self.assertEqual(
            self.page.count_label.text(),
            "0 / 6 kategori",
        )

        self.assertEqual(self.page.table.rowCount(), 0)

    @patch("ui.pages.import_coretax_page.QFileDialog.getOpenFileNames")
    def test_choose_files_accepts_multiple_files(self, mock_dialog):
        """Pilih File mendukung multi-select."""
        files = [
            str(
                Path(self.temp_dir)
                / "PIT L1 Harta Kas Setara Kas 250918.xlsx"
            ),
            str(
                Path(self.temp_dir)
                / "PIT L1 Harta Piutang 250918.xlsx"
            ),
            str(
                Path(self.temp_dir)
                / "PIT L1 Harta Investasi 250918.xlsx"
            ),
        ]

        mock_dialog.return_value = (files, "File Excel / CSV (*.xlsx *.xls *.csv)")

        self.page.choose_files()

        self.assertEqual(len(self.page.selected_files), 3)
        self.assertTrue(self.page.validate_button.isEnabled())

    @patch("ui.pages.import_coretax_page.QFileDialog.getOpenFileNames")
    @patch.object(QMessageBox, "warning")
    def test_choose_files_rejects_more_than_six(
        self,
        mock_warning,
        mock_dialog,
    ):
        """Pemilihan lebih dari enam file harus ditolak."""
        files = [
            str(Path(self.temp_dir) / f"file_{i}.xlsx")
            for i in range(7)
        ]

        mock_dialog.return_value = (
            files,
            "File Excel / CSV (*.xlsx *.xls *.csv)",
        )

        self.page.choose_files()

        mock_warning.assert_called_once()

        self.assertEqual(self.page.selected_files, [])
        self.assertFalse(self.page.validate_button.isEnabled())

    @patch("ui.pages.import_coretax_page.QFileDialog.getOpenFileNames")
    def test_choose_files_cancel(self, mock_dialog):
        """Cancel dialog tidak mengubah state."""
        mock_dialog.return_value = ([], "")

        self.page.choose_files()

        self.assertEqual(self.page.selected_files, [])
        self.assertFalse(self.page.validate_button.isEnabled())

    def test_classification_empty(self):
        """Tidak ada file berarti semua kategori belum dipilih."""
        self.page.set_files([])

        for category, label in self.page.category_labels.items():
            self.assertIn(category, label.text())
            self.assertIn("belum dipilih", label.text())

        self.assertEqual(
            self.page.count_label.text(),
            "0 / 6 kategori",
        )

    def test_classification_recognized_categories(self):
        """Kategori dikenali berdasarkan nama file Coretax."""
        files = [
            Path(self.temp_dir) / (
                "PIT L1 Harta Kas Setara Kas 250918.xlsx"
            ),
            Path(self.temp_dir) / (
                "PIT L1 Harta Piutang 250918.xlsx"
            ),
            Path(self.temp_dir) / (
                "PIT L1 Harta Investasi 250918.xlsx"
            ),
        ]

        for path in files:
            path.touch()

        self.page.set_files(files)

        self.assertEqual(
            self.page.count_label.text(),
            "3 / 6 kategori",
        )

        # Pastikan tiga kategori yang dikenali ditandai sebagai ditemukan.
        matched = 0

        for category, label in self.page.category_labels.items():
            text = label.text()

            if "— belum dipilih" not in text:
                if "✓" in text:
                    matched += 1

        self.assertEqual(matched, 3)

    def test_validate_without_files_does_nothing(self):
        """Validasi tanpa file tidak menjalankan proses."""
        importer = self.page.batch_importer

        with patch.object(importer, "validate") as mock_validate:
            self.page.validate_all()

        mock_validate.assert_not_called()
        self.assertIsNone(self.page.last_result)

    def test_reset_result_ui(self):
        """Reset hasil validasi mengosongkan preview."""
        self.page.table.setRowCount(2)
        self.page.preview_info.setText("hasil lama")
        self.page.progress.setValue(100)
        self.page.progress.setVisible(True)

        self.page._reset_result_ui()

        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertEqual(
            self.page.preview_info.text(),
            "Belum ada hasil validasi",
        )
        self.assertEqual(self.page.progress.value(), 0)
        self.assertFalse(self.page.progress.isVisible())


if __name__ == "__main__":
    unittest.main()