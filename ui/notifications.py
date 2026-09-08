from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class ToastNotification(QFrame):
    """Popup notification ringan dan non-blocking untuk aksi aplikasi.

    Toast menjadi child dari halaman aktif, sehingga tidak membuat modal dialog
    dan tidak mengganggu input user. Konfirmasi aksi destruktif tetap memakai
    QMessageBox terpisah.
    """

    STYLES = {
        "info": "background:#EAF4FD; color:#0D47A1; border:1px solid #90CAF9; border-radius:8px;",
        "success": "background:#E8F5E9; color:#1B5E20; border:1px solid #A5D6A7; border-radius:8px;",
        "warning": "background:#FFF8E1; color:#8A5A00; border:1px solid #FFE082; border-radius:8px;",
        "error": "background:#FFEBEE; color:#B71C1C; border:1px solid #EF9A9A; border-radius:8px;",
    }

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
        self.setMinimumWidth(320)
        self.setMaximumWidth(440)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(0)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-weight:600; background:transparent; border:none;")
        layout.addWidget(self.message_label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, level: str = "info", duration_ms: int = 2800):
        level = level if level in self.STYLES else "info"
        self.setStyleSheet(self.STYLES[level])
        self.message_label.setText(f"{self.PREFIX[level]}  {message}")
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._timer.start(max(800, int(duration_ms)))

    def _reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        x = max(12, parent.width() - self.width() - 18)
        self.move(x, 18)
