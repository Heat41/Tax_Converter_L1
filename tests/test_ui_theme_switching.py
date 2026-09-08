import sys
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from ui.notifications import ToastNotification
from ui.pages.settings_page import SettingsPage
from ui.theme import DARK_OVERRIDES, STYLESHEET, stylesheet_for
from ui.theme_manager import apply_theme, get_saved_theme, normalize_theme, save_theme


app = QApplication.instance() or QApplication(sys.argv)


class _FakeSettings:
    store = {}

    def __init__(self, *_args, **_kwargs):
        pass

    def value(self, key, default=None):
        return self.store.get(key, default)

    def setValue(self, key, value):
        self.store[key] = value

    def sync(self):
        pass


class TestUiThemeSwitching(unittest.TestCase):
    def tearDown(self):
        apply_theme("light")

    def test_branding_has_separate_product_and_l1_accent_styles(self):
        self.assertIn("QLabel#brandMain", STYLESHEET)
        self.assertIn("QLabel#brandAccent", STYLESHEET)
        self.assertIn("color: #2CC55E;", STYLESHEET)

    def test_dark_styles_cover_main_surfaces_and_tables(self):
        dark = stylesheet_for("dark")
        self.assertIn(DARK_OVERRIDES, dark)
        self.assertIn("background: #0F172A;", dark)
        self.assertIn("QFrame#card", dark)
        self.assertIn("QTableWidget", dark)
        self.assertIn("QLineEdit", dark)
        self.assertIn("QTabWidget#worksheetTabs::pane", dark)

    def test_theme_normalization_and_persistence(self):
        _FakeSettings.store = {}
        with patch("ui.theme_manager.QSettings", _FakeSettings):
            self.assertEqual(normalize_theme("DARK"), "dark")
            self.assertEqual(normalize_theme("unknown"), "light")
            self.assertEqual(save_theme("dark"), "dark")
            self.assertEqual(get_saved_theme(), "dark")

    def test_settings_page_switches_between_light_and_dark(self):
        page = SettingsPage("light")
        captured = []
        page.theme_changed.connect(captured.append)
        try:
            self.assertTrue(page.light_button.isChecked())
            page.dark_button.click()
            self.assertEqual(captured[-1], "dark")
            self.assertTrue(page.dark_button.isChecked())
            self.assertIn("Dark Mode", page.theme_status.text())
        finally:
            page.deleteLater()

    def test_dark_theme_uses_dark_toast_palette(self):
        apply_theme("dark")
        toast = ToastNotification()
        try:
            toast.show_message("Tema gelap aktif.", "success")
            self.assertIn("background:#153624", toast.styleSheet())
        finally:
            toast.hide()
            toast.deleteLater()


if __name__ == "__main__":
    unittest.main()
