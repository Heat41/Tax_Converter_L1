from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.database import get_db_connection
from config.settings import APP_NAME, APP_VERSION
from ui.theme import APP_FONT, STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setMinimumSize(1000, 650)
        self.setFont(APP_FONT)
        self.setStyleSheet(STYLESHEET)

        self.nav_buttons = {}
        self.pages = {}
        self._build_ui()
        self.refresh_dashboard()
        self._show_page("dashboard")

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

        navigation = (
            ("dashboard", "Dashboard"),
            ("import", "Impor Coretax"),
            ("worksheet", "Worksheet"),
            ("finalisasi", "Finalisasi"),
            ("pengaturan", "Pengaturan"),
        )

        for key, text in navigation:
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=key: self._show_page(page))
            side.addWidget(button)
            self.nav_buttons[key] = button

        side.addStretch()

        version = QLabel("Desktop Application")
        version.setObjectName("brandSub")
        side.addWidget(version)

        self.stack = QStackedWidget()
        self.pages["dashboard"] = self._build_dashboard_page()
        self.pages["import"] = self._build_placeholder_page(
            "Impor Coretax",
            "Halaman impor data Coretax akan digunakan pada Stage 2.",
            "Tahap berikutnya akan menambahkan pemilihan file, pembacaan data, validasi, dan preview hasil impor.",
        )
        self.pages["worksheet"] = self._build_placeholder_page(
            "Worksheet",
            "Halaman worksheet akan digunakan untuk pemeriksaan dan koreksi data.",
            "Fitur tabel editable, validasi, audit trail, dan filter kategori akan ditambahkan pada Stage 3.",
        )
        self.pages["finalisasi"] = self._build_placeholder_page(
            "Finalisasi",
            "Halaman finalisasi akan digunakan untuk mengunci hasil dan membuat XML.",
            "Proses finalisasi, validasi akhir, dan generator XML akan ditambahkan pada Stage 4.",
        )
        self.pages["pengaturan"] = self._build_placeholder_page(
            "Pengaturan",
            "Pengaturan aplikasi akan ditempatkan di sini.",
            "Konfigurasi aplikasi akan ditambahkan setelah alur utama selesai.",
        )

        for page in self.pages.values():
            self.stack.addWidget(page)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 30, 34, 30)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.stack)

        layout.addWidget(sidebar)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)

    def _build_dashboard_page(self):
        page = QWidget()
        main = QVBoxLayout(page)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(18)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        main.addWidget(title)

        subtitle = QLabel(
            "Kelola proses konversi data harta ke format Coretax Lampiran L-1."
        )
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
        action_layout.setSpacing(8)

        heading = QLabel("Mulai Proses")
        heading.setObjectName("sectionTitle")
        action_layout.addWidget(heading)

        desc = QLabel(
            "Impor data Coretax, periksa worksheet, lalu finalisasi hasil konversi."
        )
        desc.setObjectName("pageSubTitle")
        action_layout.addWidget(desc)

        button = QPushButton("Impor Data Coretax")
        button.setObjectName("primaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedWidth(190)
        button.clicked.connect(lambda: self._show_page("import"))
        action_layout.addWidget(button, alignment=Qt.AlignLeft)
        main.addWidget(action)

        recent = QFrame(objectName="card")
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(22, 18, 22, 18)
        recent_layout.setSpacing(10)

        recent_title = QLabel("Wajib Pajak Terbaru")
        recent_title.setObjectName("sectionTitle")
        recent_layout.addWidget(recent_title)

        self.wp_table = QTableWidget(0, 4)
        self.wp_table.setHorizontalHeaderLabels(
            ["NPWP", "Nama Wajib Pajak", "Tahun Pajak", "Status"]
        )
        self.wp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.wp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.wp_table.setSelectionMode(QTableWidget.SingleSelection)
        self.wp_table.verticalHeader().setVisible(False)
        self.wp_table.horizontalHeader().setStretchLastSection(True)
        self.wp_table.setMinimumHeight(180)
        recent_layout.addWidget(self.wp_table)
        main.addWidget(recent, 1)

        return page

    @staticmethod
    def _build_placeholder_page(title_text, subtitle_text, detail_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("pageSubTitle")
        layout.addWidget(subtitle)

        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(8)

        heading = QLabel("Tahap ini belum diaktifkan")
        heading.setObjectName("sectionTitle")
        card_layout.addWidget(heading)

        detail = QLabel(detail_text)
        detail.setObjectName("pageSubTitle")
        detail.setWordWrap(True)
        card_layout.addWidget(detail)
        layout.addWidget(card)
        layout.addStretch()
        return page

    @staticmethod
    def _card(title, value):
        card = QFrame(objectName="card")
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(6)

        label = QLabel(title)
        label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        box.addWidget(label)
        box.addWidget(value_label)
        card.value_label = value_label
        return card

    def _show_page(self, page_key):
        page = self.pages[page_key]
        self.stack.setCurrentWidget(page)
        for key, button in self.nav_buttons.items():
            button.setProperty("active", key == page_key)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def refresh_dashboard(self):
        conn = get_db_connection()
        try:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM master_wp")
            self.wp_card.value_label.setText(str(cur.fetchone()[0]))

            cur.execute("SELECT COUNT(*) FROM master_wp WHERE status_proses = 'DRAFT'")
            self.draft_card.value_label.setText(str(cur.fetchone()[0]))

            cur.execute("SELECT COUNT(*) FROM master_wp WHERE status_proses = 'FINAL'")
            self.final_card.value_label.setText(str(cur.fetchone()[0]))

            cur.execute("SELECT COUNT(*) FROM harta_l1_items WHERE is_active = 1")
            self.asset_card.value_label.setText(str(cur.fetchone()[0]))

            cur.execute("""
                SELECT npwp, nama_wp, tahun_pajak, status_proses
                FROM master_wp
                ORDER BY updated_at DESC
                LIMIT 8
            """)
            rows = cur.fetchall()

            self.wp_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                values = (
                    row["npwp"],
                    row["nama_wp"],
                    str(row["tahun_pajak"]),
                    self._status_label(row["status_proses"]),
                )
                for column_index, value in enumerate(values):
                    self.wp_table.setItem(
                        row_index,
                        column_index,
                        QTableWidgetItem(value or "-"),
                    )

            self.wp_table.resizeColumnsToContents()
        finally:
            conn.close()

    @staticmethod
    def _status_label(status):
        return {
            "BELUM_IMPOR": "Belum Impor",
            "DRAFT": "Draft",
            "FINAL": "Final",
        }.get(status, status or "-")
