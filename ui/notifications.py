from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout


class ToastNotification(QFrame):
    """Popup notification ringan dan non-blocking untuk aksi aplikasi.

    Seluruh feedback aksi user sebaiknya menggunakan toast ini agar konsisten.
    Konfirmasi aksi destruktif tetap memakai QMessageBox karena membutuhkan
    keputusan eksplisit dari user.
    """

    LIGHT_STYLES = {
        "info": "background:#EAF4FD; color:#0D47A1; border:1px solid #90CAF9; border-radius:10px;",
        "success": "background:#E8F5E9; color:#1B5E20; border:1px solid #A5D6A7; border-radius:10px;",
        "warning": "background:#FFF8E1; color:#8A5A00; border:1px solid #FFE082; border-radius:10px;",
        "error": "background:#FFEBEE; color:#B71C1C; border:1px solid #EF9A9A; border-radius:10px;",
    }
    DARK_STYLES = {
        "info": "background:#132A46; color:#BFDBFE; border:1px solid #315C87; border-radius:10px;",
        "success": "background:#153624; color:#BBF7D0; border:1px solid #2E6B49; border-radius:10px;",
        "warning": "background:#3A2C12; color:#FDE68A; border:1px solid #705521; border-radius:10px;",
        "error": "background:#3B1D24; color:#FECACA; border:1px solid #7F3545; border-radius:10px;",
    }
    # Alias dipertahankan untuk kompatibilitas test/lapisan lama.
    STYLES = LIGHT_STYLES

    PREFIX = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✕",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toastNotification")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMinimumWidth(350)
        self.setMaximumWidth(500)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(0)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(
            "font-size:13px; font-weight:700; background:transparent; border:none;"
        )
        layout.addWidget(self.message_label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    @staticmethod
    def _current_theme() -> str:
        app = QApplication.instance()
        if app is None:
            return "light"
        theme = str(app.property("appTheme") or "light").strip().lower()
        return "dark" if theme == "dark" else "light"

    def show_message(self, message: str, level: str = "info", duration_ms: int = 3200):
        level = level if level in self.LIGHT_STYLES else "info"
        styles = self.DARK_STYLES if self._current_theme() == "dark" else self.LIGHT_STYLES
        self.setStyleSheet(styles[level])
        self.message_label.setText(f"{self.PREFIX[level]}  {message}")
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._timer.start(max(1000, int(duration_ms)))

    def _reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        x = max(14, parent.width() - self.width() - 20)
        self.move(x, 20)
