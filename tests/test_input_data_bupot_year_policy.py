import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from ui.pages.input_data_page import InputDataPage


app = QApplication.instance() or QApplication(sys.argv)


class TestInputDataBupotYearPolicy(unittest.TestCase):
    def setUp(self):
        self.page = InputDataPage()
        self.page.worksheet_result = SimpleNamespace(
            npwp="6171042211890007",
            tahun_pajak=2025,
        )

    def tearDown(self):
        self.page.deleteLater()

    def test_different_bupot_year_is_allowed(self):
        rows = [
            SimpleNamespace(
                npwp_penerima="6171042211890007",
                tahun="2024",
            )
        ]
        with patch("ui.pages.input_data_page.QMessageBox.information") as info:
            self.assertTrue(self.page._validate_bupot_identity(rows))
            info.assert_called_once()

    def test_different_recipient_npwp_is_still_blocked(self):
        rows = [
            SimpleNamespace(
                npwp_penerima="0000000000000000",
                tahun="2025",
            )
        ]
        with patch("ui.pages.input_data_page.QMessageBox.warning") as warning:
            self.assertFalse(self.page._validate_bupot_identity(rows))
            warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
