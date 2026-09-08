from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.notifications import ToastNotification
from ui.theme_manager import normalize_theme


class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self, current_theme: str = "light", parent=None):
        super().__init__(parent)
        self.current_theme = normalize_theme(current_theme)
        self._build_ui()
        self._sync_theme_buttons()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("Pengaturan")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Atur tampilan aplikasi. Pilihan tema disimpan dan digunakan kembali saat aplikasi dibuka."
        )
        subtitle.setObjectName("pageSubTitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(10)

        heading = QLabel("Tampilan Aplikasi")
        heading.setObjectName("sectionTitle")
        description = QLabel(
            "Pilih tema yang nyaman digunakan. Light cocok untuk ruangan terang, sedangkan Dark mengurangi silau pada lingkungan gelap."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)
        card_layout.addWidget(heading)
        card_layout.addWidget(description)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)

        self.light_button = QPushButton("☀  Light Mode\nTampilan terang")
        self.dark_button = QPushButton("☾  Dark Mode\nTampilan gelap")
        for button in (self.light_button, self.dark_button):
            button.setObjectName("themeButton")
            button.setCheckable(True)
            button.setMinimumHeight(72)
            button.setCursor(Qt.PointingHandCursor)
            theme_row.addWidget(button, 1)

        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_group.addButton(self.light_button)
        self.theme_group.addButton(self.dark_button)
        self.light_button.clicked.connect(lambda: self._select_theme("light"))
        self.dark_button.clicked.connect(lambda: self._select_theme("dark"))
        card_layout.addLayout(theme_row)

        self.theme_status = QLabel()
        self.theme_status.setObjectName("mutedLabel")
        self.theme_status.setWordWrap(True)
        card_layout.addWidget(self.theme_status)

        layout.addWidget(card)
        layout.addStretch()

        self.toast_notification = ToastNotification(self)

    def _select_theme(self, theme: str):
        normalized = normalize_theme(theme)
        changed = normalized != self.current_theme
        self.current_theme = normalized
        self._sync_theme_buttons()
        self.theme_changed.emit(normalized)
        if changed:
            label = "Dark" if normalized == "dark" else "Light"
            self.toast_notification.show_message(
                f"Tema {label} diaktifkan dan disimpan.",
                "success",
            )

    def set_theme(self, theme: str):
        self.current_theme = normalize_theme(theme)
        self._sync_theme_buttons()

    def _sync_theme_buttons(self):
        is_dark = self.current_theme == "dark"
        self.light_button.setChecked(not is_dark)
        self.dark_button.setChecked(is_dark)
        label = "Dark Mode" if is_dark else "Light Mode"
        self.theme_status.setText(f"Tema aktif: {label}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast_notification"):
            self.toast_notification._reposition()
