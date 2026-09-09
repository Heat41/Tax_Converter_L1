from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
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
from ui.performance import optimize_table_interaction, suspended_updates
from ui.theme import APP_FONT
from ui.theme_manager import apply_theme, get_saved_theme
from ui.pages.finalization_page import FinalizationPage
from ui.pages.import_coretax_page_view import ImportCoretaxPage
from ui.pages.settings_page import SettingsPage
from ui.pages.worksheet_pph_stage7_fix import WorksheetPage


class MainWindow(QMainWindow):
    SIDEBAR_WIDTH = 250
    CONTENT_MARGIN_X = 28
    CONTENT_MARGIN_Y = 26

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setMinimumSize(1000, 650)
        self.setFont(APP_FONT)

        self.current_theme = get_saved_theme()
        apply_theme(self.current_theme)

        self.logo_path = (
            Path(__file__).resolve().parent / "assets" / "tax_converter_l1.svg"
        )
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))

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

        self.sidebar = QFrame(objectName="sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 22, 18, 18)
        side.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(12)

        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("brandLogo")
        self.brand_logo.setFixedSize(46, 46)
        if self.logo_path.exists():
            self.brand_logo.setPixmap(
                QIcon(str(self.logo_path)).pixmap(46, 46)
            )
        self.brand_logo.setAlignment(Qt.AlignCenter)
        brand_row.addWidget(self.brand_logo, alignment=Qt.AlignTop)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 1, 0, 0)
        brand_text.setSpacing(2)

        brand_name_row = QHBoxLayout()
        brand_name_row.setContentsMargins(0, 0, 0, 0)
        brand_name_row.setSpacing(5)

        self.brand_main = QLabel("TAX_CONVERTER")
        self.brand_main.setObjectName("brandMain")
        self.brand_accent = QLabel("L-1")
        self.brand_accent.setObjectName("brandAccent")
        brand_name_row.addWidget(self.brand_main)
        brand_name_row.addWidget(self.brand_accent)
        brand_name_row.addStretch()
        brand_text.addLayout(brand_name_row)

        sub = QLabel(f"v{APP_VERSION}")
        sub.setObjectName("brandSub")
        brand_text.addWidget(sub)
        brand_text.addStretch()
        brand_row.addLayout(brand_text, 1)

        side.addLayout(brand_row)

        product_desc = QLabel("Converter Harta & Kertas Kerja SPT")
        product_desc.setObjectName("sidebarCaption")
        product_desc.setWordWrap(True)
        side.addWidget(product_desc)
        side.addSpacing(20)

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
            button.setMinimumHeight(44)
            button.clicked.connect(
                lambda checked=False, page=key: self._show_page(page)
            )
            side.addWidget(button)
            self.nav_buttons[key] = button

        side.addStretch()

        version = QLabel("Internal Desktop Application")
        version.setObjectName("brandSub")
        version.setWordWrap(True)
        side.addWidget(version)

        self.stack = QStackedWidget()
        self.pages["dashboard"] = self._build_dashboard_page()

        import_page = ImportCoretaxPage()
        worksheet_page = WorksheetPage()
        import_page.harta_preview_changed.connect(
            worksheet_page.load_harta_preview
        )
        import_page.worksheet_workbook_imported.connect(
            self._on_worksheet_workbook_imported
        )

        self.pages["import"] = import_page
        self.pages["worksheet"] = worksheet_page
        self.pages["finalisasi"] = FinalizationPage(worksheet_page)

        settings_page = SettingsPage(self.current_theme)
        settings_page.theme_changed.connect(self._change_theme)
        self.pages["pengaturan"] = settings_page

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.content = QWidget()
        self.content.setObjectName("mainContent")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(
            self.CONTENT_MARGIN_X,
            self.CONTENT_MARGIN_Y,
            self.CONTENT_MARGIN_X,
            self.CONTENT_MARGIN_Y,
        )
        content_layout.setSpacing(0)
        content_layout.addWidget(self.stack)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)

    def _on_worksheet_workbook_imported(self, import_result):
        worksheet = self.pages.get("worksheet")
        pipeline = getattr(import_result, "pipeline_result", None)
        if worksheet is not None and pipeline is not None:
            worksheet.load_harta_preview(pipeline)
            self._show_page("worksheet")
            self.refresh_dashboard()

    def _build_dashboard_page(self):
        page = QWidget()
        main = QVBoxLayout(page)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        main.addWidget(title)

        subtitle = QLabel(
            "Kelola proses konversi data Harta, Worksheet, dan PPh Tahunan dalam satu alur kerja."
        )
        subtitle.setObjectName("pageSubTitle")
        subtitle.setWordWrap(True)
        main.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.wp_card = self._card("Wajib Pajak", "0")
        self.draft_card = self._card("Draft", "0")
        self.final_card = self._card("Final", "0")
        self.asset_card = self._card("Total Harta", "0")
        for card in (
            self.wp_card,
            self.draft_card,
            self.final_card,
            self.asset_card,
        ):
            cards.addWidget(card)
        main.addLayout(cards)

        action = QFrame(objectName="card")
        action_layout = QVBoxLayout(action)
        action_layout.setContentsMargins(20, 18, 20, 18)
        action_layout.setSpacing(7)

        heading = QLabel("Mulai Proses")
        heading.setObjectName("sectionTitle")
        action_layout.addWidget(heading)

        desc = QLabel(
            "Impor data Coretax atau kertas kerja yang sudah terisi, periksa Worksheet, lakukan rekonsiliasi, lalu finalisasi hasil konversi."
        )
        desc.setObjectName("pageSubTitle")
        desc.setWordWrap(True)
        action_layout.addWidget(desc)

        button = QPushButton("Impor Data Coretax / Kertas Kerja")
        button.setObjectName("primaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumWidth(220)
        button.clicked.connect(lambda: self._show_page("import"))
        action_layout.addWidget(button, alignment=Qt.AlignLeft)
        main.addWidget(action)

        recent = QFrame(objectName="card")
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(20, 16, 20, 16)
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
        optimize_table_interaction(
            self.wp_table,
            column_widths={0: 190, 1: 280, 2: 120, 3: 135},
            row_height=36,
            horizontal_step=18,
            vertical_step=18,
        )
        recent_layout.addWidget(self.wp_table)
        main.addWidget(recent, 1)

        return page

    @staticmethod
    def _build_placeholder_page(title_text, subtitle_text, detail_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("pageSubTitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
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
        card.setMinimumHeight(96)
        box = QVBoxLayout(card)
        box.setContentsMargins(17, 15, 17, 15)
        box.setSpacing(5)

        label = QLabel(title)
        label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        box.addWidget(label)
        box.addWidget(value_label)
        card.value_label = value_label
        return card

    def _change_theme(self, theme: str):
        self.current_theme = apply_theme(theme, persist=True)
        settings_page = self.pages.get("pengaturan")
        if hasattr(settings_page, "set_theme"):
            settings_page.set_theme(self.current_theme)

    def _show_page(self, page_key):
        page = self.pages[page_key]
        if page_key == "finalisasi" and hasattr(page, "refresh_page"):
            page.refresh_page()
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

            cur.execute(
                "SELECT COUNT(*) FROM master_wp WHERE status_proses = 'DRAFT'"
            )
            self.draft_card.value_label.setText(str(cur.fetchone()[0]))

            cur.execute(
                "SELECT COUNT(*) FROM master_wp WHERE status_proses = 'FINAL'"
            )
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

            with suspended_updates(self.wp_table):
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
        finally:
            conn.close()

    @staticmethod
    def _status_label(status):
        return {
            "BELUM_IMPOR": "Belum Impor",
            "DRAFT": "Draft",
            "FINAL": "Final",
        }.get(status, status or "-")
