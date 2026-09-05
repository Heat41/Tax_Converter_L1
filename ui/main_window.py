from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QVBoxLayout, QWidget
)

from config.database import get_db_connection
from config.settings import APP_NAME, APP_VERSION
from ui.theme import APP_FONT, STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setFont(APP_FONT)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self.refresh_dashboard()

    def _build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(8)

        brand = QLabel("Tax Converter")
        brand.setObjectName("brand")
        side.addWidget(brand)
        sub = QLabel(f"Lampiran L-1 • v{APP_VERSION}")
        sub.setObjectName("brandSub")
        side.addWidget(sub)
        side.addSpacing(28)

        for text in ("Dashboard", "Impor Coretax", "Worksheet", "Finalisasi", "Pengaturan"):
            button = QPushButton(text)
            button.setObjectName("navButton")
            side.addWidget(button)
        side.addStretch()

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(34, 30, 34, 30)
        main.setSpacing(18)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        main.addWidget(title)
        subtitle = QLabel("Kelola proses konversi data harta ke format Coretax Lampiran L-1.")
        subtitle.setObjectName("pageSubTitle")
        main.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.wp_card = self._card("Wajib Pajak", "0")
        self.draft_card = self._card("Draft", "0")
        self.final_card = self._card("Final", "0")
        self.asset_card = self._card("Total Harta", "0")
        for card in (self.wp_card, self.draft_card, self.final_card, self.asset_card):
            cards.addWidget(card)
        main.addLayout(cards)

        action = QFrame(objectName="card")
        action_layout = QVBoxLayout(action)
        action_layout.setContentsMargins(22, 20, 22, 20)
        heading = QLabel("Mulai Proses")
        heading.setObjectName("cardValue")
        heading.setStyleSheet("font-size:18px;")
        action_layout.addWidget(heading)
        desc = QLabel("Impor data Coretax, periksa worksheet, lalu finalisasi hasil konversi.")
        desc.setObjectName("pageSubTitle")
        action_layout.addWidget(desc)
        button = QPushButton("Impor Data Coretax")
        button.setObjectName("primaryButton")
        button.setFixedWidth(190)
        action_layout.addWidget(button, alignment=Qt.AlignLeft)
        main.addWidget(action)
        main.addStretch()

        layout.addWidget(sidebar)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)

    @staticmethod
    def _card(title, value):
        card = QFrame(objectName="card")
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 16, 18, 16)
        label = QLabel(title)
        label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        box.addWidget(label)
        box.addWidget(value_label)
        card.value_label = value_label
        return card

    def refresh_dashboard(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM master_wp")
        self.wp_card.value_label.setText(str(cur.fetchone()[0]))
        cur.execute("SELECT COUNT(*) FROM master_wp WHERE status_proses = 'DRAFT'")
        self.draft_card.value_label.setText(str(cur.fetchone()[0]))
        cur.execute("SELECT COUNT(*) FROM master_wp WHERE status_proses = 'FINAL'")
        self.final_card.value_label.setText(str(cur.fetchone()[0]))
        cur.execute("SELECT COUNT(*) FROM harta_l1_items WHERE is_active = 1")
        self.asset_card.value_label.setText(str(cur.fetchone()[0]))
        conn.close()
