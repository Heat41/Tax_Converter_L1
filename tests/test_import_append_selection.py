import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.pages.import_coretax_page import ImportCoretaxPage


app = QApplication.instance() or QApplication(sys.argv)


class TestImportAppendSelection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.page = ImportCoretaxPage()
        self.page.show()

    def tearDown(self):
        self.page.hide()
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ui.pages.QFileDialog.getOpenFileNames")
    def test_repeated_choose_files_appends_selection(self, mock_dialog):
        first = Path(self.temp_dir) / "PIT L1 Harta Kas Setara Kas 2025.xlsx"
        second = Path(self.temp_dir) / "PIT L1 Harta Piutang 2025.xlsx"
        first.touch()
        second.touch()

        mock_dialog.side_effect = [
            ([str(first)], "File Excel / CSV (*.xlsx *.xls *.csv)"),
            ([str(second)], "File Excel / CSV (*.xlsx *.xls *.csv)"),
        ]

        self.page.choose_files()
        self.page.choose_files()

        self.assertEqual(self.page.selected_files, [first.resolve(), second.resolve()])
        self.assertIn(first.name, self.page.file_label.text())
        self.assertIn(second.name, self.page.file_label.text())

    @patch("ui.pages.QFileDialog.getOpenFileNames")
    def test_repeated_same_file_is_not_duplicated(self, mock_dialog):
        first = Path(self.temp_dir) / "PIT L1 Harta Kas Setara Kas 2025.xlsx"
        first.touch()
        mock_dialog.side_effect = [
            ([str(first)], ""),
            ([str(first)], ""),
        ]

        self.page.choose_files()
        self.page.choose_files()

        self.assertEqual(self.page.selected_files, [first.resolve()])

    @patch("ui.pages.QFileDialog.getOpenFileNames")
    @patch.object(QMessageBox, "warning")
    def test_more_than_six_keeps_existing_selection(self, mock_warning, mock_dialog):
        existing = []
        for i in range(5):
            path = Path(self.temp_dir) / f"PIT L1 Harta Dummy {i}.xlsx"
            path.touch()
            existing.append(path.resolve())
        self.page.set_files(existing)

        extra1 = Path(self.temp_dir) / "extra1.xlsx"
        extra2 = Path(self.temp_dir) / "extra2.xlsx"
        extra1.touch()
        extra2.touch()
        mock_dialog.return_value = ([str(extra1), str(extra2)], "")

        self.page.choose_files()

        mock_warning.assert_called_once()
        self.assertEqual(self.page.selected_files, existing)


if __name__ == "__main__":
    unittest.main()
