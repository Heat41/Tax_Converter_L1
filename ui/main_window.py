from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.database import get_db_connection
from config.settings import APP_NAME, APP_VERSION
from ui.branding import load_app_icon
from ui.performance import optimize_scroll_area, optimize_table_interaction, suspended_updates
from ui.theme import APP_FONT
from ui.theme_manager import apply_theme, get_saved_theme
from ui.pages.finalization_page import FinalizationPage
from ui.pages.input_data_page import InputDataPage
from ui.pages.settings_page import SettingsPage
from ui.pages.worksheet_pph_stage7_fix import WorksheetPage
from ui.worksheet_export_actions import WorksheetExportActions


class MainWindow(QMainWindow):
    SIDEBAR_WIDTH = 250
    SIDEBAR_COLLAPSED_WIDTH = 76
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

        self.app_icon = load_app_icon()
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)

        self.nav_buttons = {}
        self.nav_labels = {}
        self.pages = {}
        self.sidebar_collapsed = False
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

        self.sidebar_toggle = QPushButton("‹")
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle.setFixedSize(30, 30)
        self.sidebar_toggle.setToolTip("Kecilkan sidebar")
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)
        side.addWidget(self.sidebar_toggle, alignment=Qt.AlignRight)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(12)

        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("brandLogo")
        self.brand_logo.setFixedSize(46, 46)
        if not self.app_icon.isNull():
            self.brand_logo.setPixmap(self.app_icon.pixmap(46, 46))
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

        self.brand_version = QLabel(f"v{APP_VERSION}")
        self.brand_version.setObjectName("brandSub")
        brand_text.addWidget(self.brand_version)
        brand_text.addStretch()
        brand_row.addLayout(brand_text, 1)

        side.addLayout(brand_row)

        self.product_desc = QLabel("Converter Harta & Kertas Kerja SPT")
        self.product_desc.setObjectName("sidebarCaption")
        self.product_desc.setWordWrap(True)
        side.addWidget(self.product_desc)
        side.addSpacing(20)

        navigation = (
            ("dashboard", "🏠  Dashboard"),
            ("import", "📥  Input Data"),
            ("worksheet", "📄  Worksheet"),
            ("finalisasi", "✅  Finalisasi"),
            ("pengaturan", "⚙️  Pengaturan"),
        )

        self.nav_labels = dict(navigation)
        self.nav_compact_labels = {
            "dashboard": "🏠",
            "import": "📥",
            "worksheet": "📄",
            "finalisasi": "✅",
            "pengaturan": "⚙️",
        }

        for key, text in navigation:
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(44)
            button.clicked.connect(
                lambda checked=False, page=key: self._show_page(page)
            )
            button.setToolTip(text)
            side.addWidget(button)
            self.nav_buttons[key] = button

        side.addStretch()

        self.sidebar_footer = QLabel("Internal Desktop Application")
        self.sidebar_footer.setObjectName("brandSub")
        self.sidebar_footer.setWordWrap(True)
        side.addWidget(self.sidebar_footer)

        self.stack = QStackedWidget()
        self.pages["dashboard"] = self._build_dashboard_page()

        import_page = InputDataPage()
        worksheet_page = WorksheetPage()
        self.worksheet_export_actions = WorksheetExportActions(worksheet_page, self)
        import_page.worksheet_workbook_imported.connect(
            self._on_worksheet_workbook_imported
        )
        import_page.continue_requested.connect(
            self._continue_from_input
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

    def _toggle_sidebar(self):
        self.set_sidebar_collapsed(not self.sidebar_collapsed)

    def set_sidebar_collapsed(self, collapsed: bool):
        self.sidebar_collapsed = bool(collapsed)
        width = (
            self.SIDEBAR_COLLAPSED_WIDTH
            if self.sidebar_collapsed
            else self.SIDEBAR_WIDTH
        )
        self.sidebar.setFixedWidth(width)

        side = self.sidebar.layout()
        if side is not None:
            margins = (10, 14, 10, 14) if self.sidebar_collapsed else (18, 22, 18, 18)
            side.setContentsMargins(*margins)

        self.brand_main.setVisible(not self.sidebar_collapsed)
        self.brand_accent.setVisible(not self.sidebar_collapsed)
        self.brand_version.setVisible(not self.sidebar_collapsed)
        self.product_desc.setVisible(not self.sidebar_collapsed)
        self.sidebar_footer.setVisible(not self.sidebar_collapsed)

        logo_size = 40 if self.sidebar_collapsed else 46
        self.brand_logo.setFixedSize(logo_size, logo_size)
        if not self.app_icon.isNull():
            self.brand_logo.setPixmap(self.app_icon.pixmap(logo_size, logo_size))

        for key, button in self.nav_buttons.items():
            button.setText(
                self.nav_compact_labels[key]
                if self.sidebar_collapsed
                else self.nav_labels[key]
            )
            button.setProperty("collapsed", self.sidebar_collapsed)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

        self.sidebar_toggle.setText("›" if self.sidebar_collapsed else "‹")
        self.sidebar_toggle.setToolTip(
            "Besarkan sidebar" if self.sidebar_collapsed else "Kecilkan sidebar"
        )

    def _on_worksheet_workbook_imported(self, import_result):
        worksheet = self.pages.get("worksheet")
        if worksheet is None:
            return

        if hasattr(worksheet, "load_workbook_import_result"):
            worksheet.load_workbook_import_result(import_result)
        else:
            pipeline = getattr(import_result, "pipeline_result", None)
            if pipeline is not None:
                worksheet.load_harta_preview(pipeline)

        self.refresh_dashboard()

    def _continue_from_input(self):
        worksheet = self.pages.get("worksheet")
        if worksheet is not None and hasattr(worksheet, "_load_pph_state_for_current_wp"):
            worksheet._load_pph_state_for_current_wp()
        self._show_page("worksheet")
        self.refresh_dashboard()

    def _build_dashboard_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(0, 0, 8, 8)
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
            "Masukkan Kertas Kerja dan Bupot, periksa Worksheet, lakukan rekonsiliasi, lalu finalisasi hasil konversi."
        )
        desc.setObjectName("pageSubTitle")
        desc.setWordWrap(True)
        action_layout.addWidget(desc)

        button = QPushButton("Input Kertas Kerja & Bupot")
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

        export_recent = QFrame(objectName="card")
        export_layout = QVBoxLayout(export_recent)
        export_layout.setContentsMargins(20, 16, 20, 16)
        export_layout.setSpacing(10)

        export_title = QLabel("Aktivitas Export Terbaru")
        export_title.setObjectName("sectionTitle")
        export_layout.addWidget(export_title)

        self.export_audit_table = QTableWidget(0, 7)
        self.export_audit_table.setHorizontalHeaderLabels(
            [
                "Waktu",
                "Wajib Pajak",
                "Tahun",
                "Rev",
                "Jenis Export",
                "Status",
                "Rekonsiliasi",
            ]
        )
        self.export_audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.export_audit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.export_audit_table.setSelectionMode(QTableWidget.SingleSelection)
        self.export_audit_table.verticalHeader().setVisible(False)
        self.export_audit_table.horizontalHeader().setStretchLastSection(True)
        self.export_audit_table.setMinimumHeight(170)
        optimize_table_interaction(
            self.export_audit_table,
            column_widths={
                0: 145,
                1: 230,
                2: 90,
                3: 65,
                4: 155,
                5: 90,
                6: 115,
            },
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        export_layout.addWidget(self.export_audit_table)
        main.addWidget(export_recent, 1)
        main.addStretch()

        scroll.setWidget(content)
        optimize_scroll_area(scroll, vertical_step=24)
        page_layout.addWidget(scroll)

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
        if page_key == "dashboard":
            self.refresh_dashboard()
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

            try:
                cur.execute("""
                    SELECT created_at, nama_wp, tahun_pajak, revision,
                           export_type, status, reconciliation_status
                    FROM export_audit_log
                    ORDER BY id DESC
                    LIMIT 8
                """)
                export_rows = cur.fetchall()
            except Exception:
                # Kompatibilitas untuk database lama/test fixture yang belum
                # memiliki schema audit trail. Dashboard tetap harus bisa dibuka.
                export_rows = []

            with suspended_updates(self.export_audit_table):
                self.export_audit_table.setRowCount(len(export_rows))
                for row_index, row in enumerate(export_rows):
                    export_type = {
                        "FORMAT_LAMA_PDF": "Format Lama",
                        "PAKET_CORETAX": "Paket Coretax",
                    }.get(row["export_type"], row["export_type"] or "-")
                    values = (
                        row["created_at"] or "-",
                        row["nama_wp"] or "-",
                        str(row["tahun_pajak"] or "-"),
                        f"R{row['revision']}",
                        export_type,
                        row["status"] or "-",
                        row["reconciliation_status"] or "-",
                    )
                    for column_index, value in enumerate(values):
                        self.export_audit_table.setItem(
                            row_index,
                            column_index,
                            QTableWidgetItem(str(value)),
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
