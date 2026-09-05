from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
)

from core.coretax_reader import CoretaxReader, CoretaxReaderError
from core.validation.batch import CoretaxBatchImporter
from core.validation.models import BatchImportResult
from core.validation.rules import CATEGORIES


class ImportCoretaxPage(QWidget):
    """UI impor Coretax enam kategori, Stage 3B."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reader = CoretaxReader()
        self.batch_importer = CoretaxBatchImporter(reader=self.reader)
        self.selected_files: List[Path] = []
        self.last_result: Optional[BatchImportResult] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        title = QLabel("Impor Coretax")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Pilih folder atau beberapa file Coretax. Sistem akan mengenali kategori secara otomatis."
        )
        subtitle.setObjectName("pageSubTitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        source_card = QFrame()
        source_card.setObjectName("card")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(24, 24, 24, 24)
        source_layout.setSpacing(14)

        source_title = QLabel("1. Pilih Sumber Coretax")
        source_title.setObjectName("sectionTitle")
        self.file_label = QLabel("Belum ada file yang dipilih")
        self.file_label.setObjectName("mutedLabel")
        self.file_label.setWordWrap(True)

        buttons = QHBoxLayout()
        folder_button = QPushButton("📁 Pilih Folder")
        folder_button.setObjectName("primaryButton")
        folder_button.clicked.connect(self.choose_folder)
        file_button = QPushButton("📄 Pilih File")
        file_button.setObjectName("primaryButton")
        file_button.clicked.connect(self.choose_files)
        clear_button = QPushButton("Bersihkan")
        clear_button.clicked.connect(self.clear_selection)
        self.validate_button = QPushButton("Validasi Semua")
        self.validate_button.setObjectName("primaryButton")
        self.validate_button.setEnabled(False)
        self.validate_button.clicked.connect(self.validate_all)
        buttons.addWidget(folder_button)
        buttons.addWidget(file_button)
        buttons.addWidget(clear_button)
        buttons.addStretch()
        buttons.addWidget(self.validate_button)

        source_layout.addWidget(source_title)
        source_layout.addWidget(self.file_label)
        source_layout.addLayout(buttons)
        layout.addWidget(source_card)

        category_card = QFrame()
        category_card.setObjectName("card")
        category_layout = QVBoxLayout(category_card)
        category_layout.setContentsMargins(24, 24, 24, 24)
        category_layout.setSpacing(8)
        category_title = QLabel("2. Kategori Coretax")
        category_title.setObjectName("sectionTitle")
        category_layout.addWidget(category_title)
        self.category_labels: Dict[str, QLabel] = {}
        for category in CATEGORIES:
            label = QLabel(f"— {category}")
            label.setObjectName("mutedLabel")
            self.category_labels[category] = label
            category_layout.addWidget(label)
        self.count_label = QLabel("0 / 6 kategori")
        self.count_label.setObjectName("sectionTitle")
        category_layout.addWidget(self.count_label)
        layout.addWidget(category_card)

        progress_card = QFrame()
        progress_card.setObjectName("card")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(24, 20, 24, 20)
        progress_layout.setSpacing(10)
        progress_title = QLabel("3. Status Proses")
        progress_title.setObjectName("sectionTitle")
        self.status_label = QLabel("Menunggu sumber data...")
        self.status_label.setObjectName("mutedLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        progress_layout.addWidget(progress_title)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress)
        layout.addWidget(progress_card)

        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(24, 24, 24, 24)
        preview_layout.setSpacing(12)
        header = QHBoxLayout()
        preview_title = QLabel("4. Hasil Validasi")
        preview_title.setObjectName("sectionTitle")
        self.preview_info = QLabel("Belum ada hasil validasi")
        self.preview_info.setObjectName("mutedLabel")
        header.addWidget(preview_title)
        header.addStretch()
        header.addWidget(self.preview_info)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Kategori", "File", "Status", "Baris", "Pesan"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        preview_layout.addLayout(header)
        preview_layout.addWidget(self.table)
        layout.addWidget(preview_card, 1)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Coretax")
        if not folder:
            return
        try:
            files = self.batch_importer.discover_files(Path(folder))
            # A folder may contain unrelated spreadsheets. Only six recognized
            # categories count toward the six-file limit.
            recognized = [p for p in files if self.batch_importer.detect_category(p)]
            if len(recognized) > 6:
                QMessageBox.warning(self, "Terlalu Banyak File", "Folder mengandung lebih dari 6 file Coretax yang dikenali.")
                return
            self.set_files(recognized)
            self.status_label.setText(f"Folder dipindai: {len(recognized)} file Coretax dikenali.")
        except Exception as exc:
            QMessageBox.warning(self, "Folder Tidak Valid", str(exc))

    def choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih File Coretax (maksimal 6)",
            "",
            "File Excel / CSV (*.xlsx *.xls *.csv);;Semua File (*.*)",
        )
        if not files:
            return
        if len(files) > 6:
            QMessageBox.warning(self, "Batas File", "Maksimal 6 file dapat dipilih sekaligus.")
            return
        self.set_files([Path(p) for p in files])

    def set_files(self, files: List[Path]):
        self.selected_files = list(dict.fromkeys(Path(p).resolve() for p in files))
        self.last_result = None
        self.validate_button.setEnabled(bool(self.selected_files))
        self.file_label.setText("\n".join(p.name for p in self.selected_files) or "Belum ada file yang dipilih")
        self._reset_result_ui()
        self._show_classification()

    def _show_classification(self):
        classified = {category: [] for category in CATEGORIES}
        for path in self.selected_files:
            category = self.batch_importer.detect_category(path)
            if category:
                classified[category].append(path)
        found = 0
        for category in CATEGORIES:
            paths = classified[category]
            if len(paths) == 1:
                self.category_labels[category].setText(f"✓ {category} — {paths[0].name}")
                found += 1
            elif len(paths) > 1:
                self.category_labels[category].setText(f"⚠ {category} — {len(paths)} file (duplikat)")
            else:
                self.category_labels[category].setText(f"— {category} — belum dipilih")
        self.count_label.setText(f"{found} / 6 kategori")

    def validate_all(self):
        if not self.selected_files:
            return
        self.progress.setVisible(True)
        self.progress.setValue(10)
        self.status_label.setText("Mendeteksi kategori dan membaca file Coretax...")
        try:
            result = self.batch_importer.validate(self.selected_files)
            self.last_result = result
            self.progress.setValue(100)
            self._render_result(result)
            if result.is_valid:
                self.status_label.setText("Validasi selesai. Tidak ada error validasi.")
            else:
                self.status_label.setText(f"Validasi selesai dengan {len(result.errors)} error.")
        except Exception as exc:
            self.progress.setVisible(False)
            self.status_label.setText(f"Gagal melakukan validasi: {exc}")
            QMessageBox.critical(self, "Error Validasi", str(exc))

    def _render_result(self, result: BatchImportResult):
        self.table.clearContents()
        rows = []
        for category in CATEGORIES:
            item = result.category_results.get(category)
            if not item or item.status == "MISSING":
                continue
            filename = item.file_path.name if item.file_path else "-"
            row_count = item.read_result.total_rows if item.read_result else 0
            message = item.message or ("Valid" if item.status == "VALID" else "")
            rows.append((category, filename, item.status, str(row_count), message))
        self.table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.preview_info.setText(
            f"{result.found_count}/6 kategori • {result.total_rows} baris • "
            f"{len(result.errors)} error • {len(result.warnings)} warning"
        )
        self._show_classification()

    def _reset_result_ui(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.preview_info.setText("Belum ada hasil validasi")
        self.progress.setVisible(False)
        self.progress.setValue(0)

    def clear_selection(self):
        self.selected_files = []
        self.last_result = None
        self.file_label.setText("Belum ada file yang dipilih")
        self.status_label.setText("Menunggu sumber data...")
        self.validate_button.setEnabled(False)
        for category in CATEGORIES:
            self.category_labels[category].setText(f"— {category} — belum dipilih")
        self.count_label.setText("0 / 6 kategori")
        self._reset_result_ui()
