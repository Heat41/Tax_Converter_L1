from pathlib import Path
from typing import Optional

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
    QComboBox,
)

from core.coretax_reader import (
    CoretaxReader,
    CoretaxFileInfo,
    CoretaxReadResult,
    CoretaxReaderError,
    EmptyFileError,
    EmptySheetError,
    UnsupportedFileFormatError,
    CorruptedFileError,
)


class ImportCoretaxPage(QWidget):
    """
    Halaman UI untuk mengimpor dan mem-preview data hasil ekspor Coretax (Stage 3A).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.reader = CoretaxReader()
        self.selected_file: Optional[Path] = None
        self.current_file_info: Optional[CoretaxFileInfo] = None
        self.current_result: Optional[CoretaxReadResult] = None

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
        subtitle.setObjectName("pageSubTitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # ---------------------------------------------------------
        # Card 1: Pilih File & Sheet
        # ---------------------------------------------------------
        file_card = QFrame()
        file_card.setObjectName("card")

        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(24, 24, 24, 24)
        file_layout.setSpacing(14)

        file_title = QLabel("1. Pilih File Coretax")
        file_title.setObjectName("sectionTitle")

        self.file_label = QLabel("Belum ada file yang dipilih")
        self.file_label.setObjectName("mutedLabel")
        self.file_label.setWordWrap(True)

        # Sheet selection container (tampil dinamis jika Excel)
        self.sheet_container = QWidget()
        sheet_layout = QHBoxLayout(self.sheet_container)
        sheet_layout.setContentsMargins(0, 0, 0, 0)
        sheet_layout.setSpacing(12)

        sheet_title = QLabel("Pilih Lembar (Sheet):")
        sheet_title.setObjectName("mutedLabel")
        sheet_title.setFixedWidth(140)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(220)

        sheet_layout.addWidget(sheet_title)
        sheet_layout.addWidget(self.sheet_combo)
        sheet_layout.addStretch()
        self.sheet_container.setVisible(False)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        choose_button = QPushButton("Pilih File")
        choose_button.setObjectName("primaryButton")
        choose_button.setCursor(Qt.PointingHandCursor)
        choose_button.clicked.connect(self.choose_file)

        self.import_button = QPushButton("Validasi & Impor")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.validate_import)

        button_layout.addWidget(choose_button)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch()

        file_layout.addWidget(file_title)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.sheet_container)
        file_layout.addLayout(button_layout)

        layout.addWidget(file_card)

        # ---------------------------------------------------------
        # Card 2: Status Proses
        # ---------------------------------------------------------
        progress_card = QFrame()
        progress_card.setObjectName("card")

        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(24, 20, 24, 20)
        progress_layout.setSpacing(10)

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

        # ---------------------------------------------------------
        # Card 3: Dynamic Preview Table
        # ---------------------------------------------------------
        preview_card = QFrame()
        preview_card.setObjectName("card")

        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(24, 24, 24, 24)
        preview_layout.setSpacing(14)

        preview_header_layout = QHBoxLayout()
        preview_title = QLabel("3. Preview Data")
        preview_title.setObjectName("sectionTitle")

        self.preview_info_label = QLabel("Belum ada data untuk ditampilkan")
        self.preview_info_label.setObjectName("mutedLabel")

        preview_header_layout.addWidget(preview_title)
        preview_header_layout.addStretch()
        preview_header_layout.addWidget(self.preview_info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        preview_layout.addLayout(preview_header_layout)
        preview_layout.addWidget(self.table)

        layout.addWidget(preview_card, 1)

    def choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Coretax",
            "",
            "File Excel / CSV (*.xlsx *.xls *.csv);;File Excel (*.xlsx *.xls);;File CSV (*.csv);;Semua File (*.*)",
        )

        if not file_path:
            return

        self.load_file(file_path)

    def load_file(self, file_path):
        """
        Memeriksa dan memuat file yang dipilih pengguna ke state UI.
        """
        try:
            info = self.reader.inspect_file(file_path)
            self.selected_file = info.file_path
            self.current_file_info = info

            # Update UI info
            if info.is_excel:
                self.file_label.setText(
                    f"File: {info.file_path} ({len(info.sheets)} sheet terdeteksi)"
                )
                self.sheet_combo.clear()
                self.sheet_combo.addItems(info.sheets)
                self.sheet_container.setVisible(len(info.sheets) > 1)
            else:
                self.file_label.setText(f"File: {info.file_path} (CSV)")
                self.sheet_container.setVisible(False)

            self.status_label.setText(f"File '{info.file_name}' siap dibaca.")
            self.import_button.setEnabled(True)

            # Reset preview
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.preview_info_label.setText("Klik 'Validasi & Impor' untuk memuat preview")
            self.progress.setVisible(False)
            self.progress.setValue(0)

        except (
            UnsupportedFileFormatError,
            EmptyFileError,
            CorruptedFileError,
            FileNotFoundError,
            CoretaxReaderError,
        ) as err:
            self.selected_file = None
            self.current_file_info = None
            self.import_button.setEnabled(False)
            self.sheet_container.setVisible(False)
            self.file_label.setText("File tidak valid atau tidak dapat dibuka.")
            self.status_label.setText(f"Gagal memeriksa file: {err}")
            QMessageBox.warning(self, "Peringatan File", str(err))
        except Exception as err:
            self.selected_file = None
            self.current_file_info = None
            self.import_button.setEnabled(False)
            self.sheet_container.setVisible(False)
            self.file_label.setText("Terjadi kesalahan saat memeriksa file.")
            self.status_label.setText(f"Error tidak terduga: {err}")
            QMessageBox.critical(self, "Error Tidak Terduga", f"Gagal memeriksa file:\n{err}")

    def validate_import(self):
        if not self.selected_file or not self.current_file_info:
            return

        self.progress.setVisible(True)
        self.progress.setValue(20)
        self.status_label.setText("Membaca data file Coretax...")

        try:
            # Tentukan sheet yang akan dibaca jika Excel
            selected_sheet = None
            if self.current_file_info.is_excel and self.sheet_combo.count() > 0:
                selected_sheet = self.sheet_combo.currentText()

            self.progress.setValue(50)
            result = self.reader.read(self.selected_file, sheet_name=selected_sheet)
            self.current_result = result

            self.progress.setValue(80)

            # Render data secara dinamis ke QTableWidget
            self.table.clear()
            self.table.setColumnCount(result.total_columns)
            self.table.setHorizontalHeaderLabels(result.headers)
            self.table.setRowCount(result.total_rows)

            for row_idx, row_data in enumerate(result.rows):
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value))
                    self.table.setItem(row_idx, col_idx, item)

            self.table.resizeColumnsToContents()

            self.progress.setValue(100)

            # Update informasi preview dan status
            sheet_info = f" [Sheet: {result.sheet_name}]" if result.sheet_name else ""
            self.preview_info_label.setText(
                f"{result.total_rows} baris • {result.total_columns} kolom"
            )
            self.status_label.setText(
                f"Selesai: Membaca '{result.file_name}'{sheet_info} ({result.total_rows} baris, {result.total_columns} kolom)."
            )

            QMessageBox.information(
                self,
                "Pembacaan Berhasil",
                f"File '{result.file_name}'{sheet_info} berhasil dibaca.\n"
                f"Ditemukan {result.total_rows} baris dan {result.total_columns} kolom data.",
            )

        except (
            EmptySheetError,
            EmptyFileError,
            CorruptedFileError,
            UnsupportedFileFormatError,
            CoretaxReaderError,
        ) as err:
            self.progress.setVisible(False)
            self.status_label.setText(f"Gagal membaca file: {err}")
            QMessageBox.warning(self, "Peringatan Pembacaan", str(err))
        except Exception as err:
            self.progress.setVisible(False)
            self.status_label.setText(f"Error tidak terduga saat membaca file: {err}")
            QMessageBox.critical(self, "Error Tidak Terduga", f"Terjadi kesalahan:\n{err}")