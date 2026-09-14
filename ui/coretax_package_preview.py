from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.coretax_official_schema import get_official_schema
from core.reverse_coretax_mapping import CATEGORY_ORDER, ReverseCoretaxPackage
from ui.performance import optimize_table_interaction


class CoretaxPackagePreviewDialog(QDialog):
    """Stage 8D.4N - preview ringkas paket Coretax dari snapshot FINAL."""

    def __init__(self, package: ReverseCoretaxPackage, parent=None):
        super().__init__(parent)
        self.package = package

        self.setWindowTitle("Preview Paket Coretax")
        self.resize(1120, 720)
        self.setMinimumSize(860, 560)

        self._build_ui()
        self._populate()

    @staticmethod
    def _money(value) -> str:
        try:
            return "Rp " + f"{float(value or 0):,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            return "Rp 0"

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        summary = QFrame(objectName="card")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(18)

        self.identity_label = QLabel()
        self.identity_label.setObjectName("mutedLabel")
        self.identity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.category_label = QLabel()
        self.category_label.setObjectName("mutedLabel")

        self.row_count_label = QLabel()
        self.row_count_label.setObjectName("mutedLabel")

        self.status_label = QLabel()
        self.status_label.setObjectName("mutedLabel")

        summary_layout.addWidget(self.identity_label)
        summary_layout.addStretch()
        summary_layout.addWidget(self.category_label)
        summary_layout.addWidget(self.row_count_label)
        summary_layout.addWidget(self.status_label)
        root.addWidget(summary)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("worksheetTabs")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.note_label = QLabel(
            "Preview membaca snapshot FINAL dan tidak membuat file export."
        )
        self.note_label.setObjectName("mutedLabel")
        footer.addWidget(self.note_label, 1)

        close_button = QPushButton("Tutup")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def _populate(self):
        active_categories = [
            category
            for category in CATEGORY_ORDER
            if self.package.rows_by_category.get(category)
        ]

        self.identity_label.setText(
            f"{self.package.nama_wp or '-'} • "
            f"{self.package.npwp or '-'} • "
            f"Tahun {self.package.tahun_pajak} • "
            f"Revision {self.package.revision}"
        )
        self.category_label.setText(
            f"{len(active_categories)} kategori aktif"
        )
        self.row_count_label.setText(
            f"{self.package.total_rows} baris"
        )
        self.status_label.setText(
            "SIAP EXPORT" if self.package.can_export else "BELUM SIAP"
        )

        for category in active_categories:
            self.tabs.addTab(
                self._build_category_tab(category),
                f"{category} ({len(self.package.rows_by_category[category])})",
            )

        if not active_categories:
            empty = QLabel("Tidak ada kategori Harta berisi data.")
            empty.setObjectName("mutedLabel")
            empty.setAlignment(Qt.AlignCenter)
            self.tabs.addTab(empty, "Tidak Ada Data")

    def _build_category_tab(self, category: str) -> QWidget:
        rows = self.package.rows_by_category.get(category, [])
        schema = get_official_schema(category)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(10)

        info = QLabel(
            "Output: Excel"
            + (" + XML" if schema.has_xml_reference else " (XML belum memiliki kontrak resmi)")
            + f" • Target sheet: {schema.excel_sheet}"
        )
        info.setObjectName("mutedLabel")
        layout.addWidget(info)

        table = QTableWidget(len(rows), 8)
        table.setHorizontalHeaderLabels(
            [
                "NO",
                "KODE",
                "NAMA HARTA",
                "AKUN / KETERANGAN",
                "ATAS NAMA",
                "BANK / INSTITUSI",
                "TAHUN",
                "NILAI",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)

        for row_index, item in enumerate(rows):
            values = (
                item.nomor,
                item.kode_harta,
                item.nama_harta or "-",
                item.nomor_akun_keterangan or "-",
                item.atas_nama or "-",
                item.nama_bank or "-",
                item.tahun_perolehan or "-",
                self._money(item.nilai),
            )
            for column_index, value in enumerate(values):
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(str(value)),
                )

        optimize_table_interaction(
            table,
            column_widths={
                0: 60,
                1: 90,
                2: 210,
                3: 230,
                4: 180,
                5: 190,
                6: 90,
                7: 150,
            },
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        layout.addWidget(table, 1)
        return page
