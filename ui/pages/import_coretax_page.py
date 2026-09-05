from pathlib import Path


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QProgressBar,
)


class ImportCoretaxPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_file = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        title = QLabel("Impor Coretax")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Impor data hasil ekspor Coretax untuk diproses ke Lampiran L-1."
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # File selection card
        file_card = QFrame()
        file_card.setObjectName("card")

        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(24, 24, 24, 24)
        file_layout.setSpacing(12)

        file_title = QLabel("1. Pilih File Coretax")
        file_title.setObjectName("sectionTitle")

        self.file_label = QLabel("Belum ada file yang dipilih")
        self.file_label.setObjectName("mutedLabel")
        self.file_label.setWordWrap(True)

        button_layout = QHBoxLayout()

        choose_button = QPushButton("Pilih File")
        choose_button.setObjectName("primaryButton")
        choose_button.clicked.connect(self.choose_file)

        self.import_button = QPushButton("Validasi & Impor")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.validate_import)

        button_layout.addWidget(choose_button)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch()

        file_layout.addWidget(file_title)
        file_layout.addWidget(self.file_label)
        file_layout.addLayout(button_layout)

        layout.addWidget(file_card)

        # Progress
        progress_card = QFrame()
        progress_card.setObjectName("card")

        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(24, 24, 24, 24)

        progress_title = QLabel("2. Status Proses")
        progress_title.setObjectName("sectionTitle")

        self.status_label = QLabel("Menunggu file...")
        self.status_label.setObjectName("mutedLabel")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

        progress_layout.addWidget(progress_title)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress)

        layout.addWidget(progress_card)

        # Preview
        preview_card = QFrame()
        preview_card.setObjectName("card")

        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(24, 24, 24, 24)

        preview_title = QLabel("3. Preview Data")
        preview_title.setObjectName("sectionTitle")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [
                "Kategori",
                "Kode Harta",
                "Nama Harta",
                "Nilai",
            ]
        )

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.table)

        layout.addWidget(preview_card, 1)

    def choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Coretax",
            "",
            "File Excel (*.xlsx *.xls);;File CSV (*.csv);;Semua File (*.*)",
        )

        if not file_path:
            return

        self.selected_file = Path(file_path)

        self.file_label.setText(str(self.selected_file))
        self.status_label.setText("File berhasil dipilih.")
        self.import_button.setEnabled(True)

    def validate_import(self):
        if not self.selected_file:
            return

        self.progress.setVisible(True)
        self.progress.setValue(25)
        self.status_label.setText("Memvalidasi file...")

        # ---------------------------------------------------------
        # TODO:
        # Di sini nanti kamu hubungkan dengan parser Coretax.
        # Jangan langsung simpan ke database sebelum validasi selesai.
        # ---------------------------------------------------------

        self.progress.setValue(60)

        # Data dummy sementara untuk menguji UI.
        preview_data = [
            ["Kas", "L01", "Kas dan Setara Kas", "100000000"],
            ["Piutang", "L02", "Piutang Usaha", "250000000"],
            ["Kendaraan", "L03", "Kendaraan", "350000000"],
        ]

        self.table.setRowCount(len(preview_data))

        for row, data in enumerate(preview_data):
            for column, value in enumerate(data):
                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self.progress.setValue(100)
        self.status_label.setText(
            f"Validasi selesai: {len(preview_data)} data ditemukan."
        )

        QMessageBox.information(
            self,
            "Validasi Berhasil",
            "File berhasil divalidasi dan data tersedia untuk preview.",
        )