import inspect
import unittest
from pathlib import Path

from PySide6.QtGui import QIcon

import ui.main_window as main_window_module
from ui.main_window import MainWindow
from ui.theme import STYLESHEET


class TestUiLayoutBranding(unittest.TestCase):
    def test_l1_logo_asset_exists_and_is_loadable(self):
        logo_path = (
            Path(main_window_module.__file__).resolve().parent
            / "assets"
            / "tax_converter_l1.svg"
        )
        self.assertTrue(logo_path.exists())
        self.assertFalse(QIcon(str(logo_path)).isNull())

    def test_main_layout_uses_readable_proportions(self):
        self.assertEqual(MainWindow.SIDEBAR_WIDTH, 250)
        self.assertEqual(MainWindow.CONTENT_MARGIN_X, 28)
        self.assertEqual(MainWindow.CONTENT_MARGIN_Y, 26)

    def test_sidebar_branding_matches_global_theme(self):
        self.assertIn("QLabel#brandLogo", STYLESHEET)
        self.assertIn("QLabel#sidebarCaption", STYLESHEET)
        self.assertIn('QPushButton#navButton[active="true"]', STYLESHEET)
        self.assertIn("background: #2563EB;", STYLESHEET)

    def test_dashboard_refresh_does_not_resize_columns_to_contents(self):
        source = inspect.getsource(MainWindow.refresh_dashboard)
        self.assertNotIn("resizeColumnsToContents", source)
        self.assertIn("suspended_updates", source)


if __name__ == "__main__":
    unittest.main()
