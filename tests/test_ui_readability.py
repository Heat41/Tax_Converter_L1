import sys
import unittest

from PySide6.QtWidgets import QApplication

from ui.notifications import ToastNotification
from ui.theme import STYLESHEET


app = QApplication.instance() or QApplication(sys.argv)


class TestUiReadability(unittest.TestCase):
    def test_navigation_and_titles_use_readable_sizes(self):
        self.assertIn("QPushButton#navButton", STYLESHEET)
        self.assertIn("font-size: 14px;", STYLESHEET)
        self.assertIn("QLabel#pageTitle", STYLESHEET)
        self.assertIn("font-size: 29px;", STYLESHEET)
        self.assertIn("QLabel#sectionTitle", STYLESHEET)
        self.assertIn("font-size: 18px;", STYLESHEET)
        self.assertIn("font-weight: 700;", STYLESHEET)

    def test_worksheet_status_labels_are_bold(self):
        start = STYLESHEET.index("QLabel#mutedLabel")
        end = STYLESHEET.index("QLabel#sectionTitle", start)
        muted_block = STYLESHEET[start:end]
        self.assertIn("font-size: 13px;", muted_block)
        self.assertIn("font-weight: 700;", muted_block)

    def test_toast_popup_is_large_enough_to_read(self):
        toast = ToastNotification()
        try:
            self.assertGreaterEqual(toast.minimumWidth(), 350)
            self.assertGreaterEqual(toast.maximumWidth(), 500)
            toast.show_message("Data berhasil disimpan.", "success")
            self.assertTrue(toast.isVisible())
            self.assertTrue(toast._timer.isActive())
            self.assertIn("font-size:13px", toast.message_label.styleSheet())
            self.assertIn("font-weight:700", toast.message_label.styleSheet())
        finally:
            toast.hide()
            toast.deleteLater()


if __name__ == "__main__":
    unittest.main()
