from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.bupot_pdf_importer import BupotPdfImporter
from core.rekap_bupot_importer import RekapBupotImporter
from core.selectable_worksheet_importer import SelectableWorksheetWorkbookImporter
from core.worksheet_pph_state import WorksheetBupotRow


class InputDataPage(QWidget):
    """Halaman input sederhana: Kertas Kerja + Bupot."""

    worksheet_workbook_imported = Signal(object)
    continue_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worksheet_importer = SelectableWorksheetWorkbookImporter()
        self.rekap_importer = RekapBupotImporter()
        self.pdf_importer = BupotPdfImporter()

        self.worksheet_path: Optional[Path] = None
        self.worksheet_result = None
        self.rekap_path: Optional[Path] = None
        self.single_bupot_paths: List[Path] = []
        self.bupot_count = 0

        self._build_ui()
        self._refresh_summary()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 4, 8, 24)
        layout.setSpacing(16)

        title = QLabel("Input Data")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Masukkan Kertas Kerja dan Bupot. Pilih sendiri sheet Kertas Kerja yang akan dipakai."
        )
        subtitle.setObjectName("pageSubTitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_worksheet_card())
        layout.addWidget(self._build_bupot_card())
        layout.addWidget(self._build_summary_card())
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_worksheet_card(self):
        card = QFrame(objectName="card")
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 18, 22, 18)
        box.setSpacing(10)

        title = QLabel("1. Kertas Kerja")
        title.setObjectName("sectionTitle")
        note = QLabel(
            "Pilih file Excel, lalu pilih sheet data/tahun. Sheet SIMULASI I tetap dibaca sebagai sumber Harta."
        )
        note.setObjectName("mutedLabel")
        note.setWordWrap(True)

        self.worksheet_file_label = QLabel("Belum ada file Kertas Kerja")
        self.worksheet_file_label.setObjectName("mutedLabel")
        self.worksheet_file_label.setWordWrap(True)

        file_row = QHBoxLayout()
        self.choose_worksheet_button = QPushButton("Pilih Kertas Kerja")
        self.choose_worksheet_button.setObjectName("secondaryButton")
        self.choose_worksheet_button.clicked.connect(self.choose_worksheet)
        file_row.addWidget(self.choose_worksheet_button)
        file_row.addStretch()

        sheet_row = QHBoxLayout()
        sheet_label = QLabel("Sheet data:")
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(260)
        self.sheet_combo.setEnabled(False)
        self.import_worksheet_button = QPushButton("Import Kertas Kerja")
        self.import_worksheet_button.setObjectName("primaryButton")
        self.import_worksheet_button.setEnabled(False)
        self.import_worksheet_button.clicked.connect(self.import_worksheet)
        sheet_row.addWidget(sheet_label)
        sheet_row.addWidget(self.sheet_combo, 1)
        sheet_row.addWidget(self.import_worksheet_button)

        self.simulasi_status = QLabel("SIMULASI I: belum diperiksa")
        self.simulasi_status.setObjectName("mutedLabel")
        self.worksheet_status = QLabel("Belum diimport")
        self.worksheet_status.setObjectName("mutedLabel")
        self.worksheet_status.setWordWrap(True)

        box.addWidget(title)
        box.addWidget(note)
        box.addWidget(self.worksheet_file_label)
        box.addLayout(file_row)
        box.addLayout(sheet_row)
        box.addWidget(self.simulasi_status)
        box.addWidget(self.worksheet_status)
        return card

    def _build_bupot_card(self):
        card = QFrame(objectName="card")
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 18, 22, 18)
        box.setSpacing(10)

        title = QLabel("2. Bupot")
        title.setObjectName("sectionTitle")
        note = QLabel(
            "Gunakan Rekap Bupot Excel atau upload Bupot PDF satuan. Keduanya dinormalisasi ke field Rekap Bupot yang sama."
        )
        note.setObjectName("mutedLabel")
        note.setWordWrap(True)

        rekap_row = QHBoxLayout()
        self.rekap_label = QLabel("Rekap Bupot: belum dipilih")
        self.rekap_label.setObjectName("mutedLabel")
        self.choose_rekap_button = QPushButton("Pilih Rekap Bupot")
        self.choose_rekap_button.setObjectName("secondaryButton")
        self.choose_rekap_button.clicked.connect(self.choose_rekap)
        self.import_rekap_button = QPushButton("Import Rekap")
        self.import_rekap_button.setObjectName("primaryButton")
        self.import_rekap_button.setEnabled(False)
        self.import_rekap_button.clicked.connect(self.import_rekap)
        rekap_row.addWidget(self.rekap_label, 1)
        rekap_row.addWidget(self.choose_rekap_button)
        rekap_row.addWidget(self.import_rekap_button)

        single_row = QHBoxLayout()
        self.single_label = QLabel("Bupot satuan: belum dipilih")
        self.single_label.setObjectName("mutedLabel")
        self.choose_single_button = QPushButton("Pilih PDF Bupot")
        self.choose_single_button.setObjectName("secondaryButton")
        self.choose_single_button.clicked.connect(self.choose_single_bupot)
        self.import_single_button = QPushButton("Import PDF")
        self.import_single_button.setObjectName("primaryButton")
        self.import_single_button.setEnabled(False)
        self.import_single_button.clicked.connect(self.import_single_bupot)
        single_row.addWidget(self.single_label, 1)
        single_row.addWidget(self.choose_single_button)
        single_row.addWidget(self.import_single_button)

        self.bupot_status = QLabel("Import Kertas Kerja terlebih dahulu agar NPWP menjadi acuan.")
        self.bupot_status.setObjectName("mutedLabel")
        self.bupot_status.setWordWrap(True)

        box.addWidget(title)
        box.addWidget(note)
        box.addLayout(rekap_row)
        box.addLayout(single_row)
        box.addWidget(self.bupot_status)
        return card

    def _build_summary_card(self):
        card = QFrame(objectName="card")
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 18, 22, 18)
        box.setSpacing(8)

        title = QLabel("3. Ringkasan")
        title.setObjectName("sectionTitle")
        self.identity_summary = QLabel("WP: -")
        self.identity_summary.setObjectName("mutedLabel")
        self.sheet_summary = QLabel("Sheet: -")
        self.sheet_summary.setObjectName("mutedLabel")
        self.harta_summary = QLabel("Harta: 0 baris")
        self.harta_summary.setObjectName("mutedLabel")
        self.bupot_summary = QLabel("Bupot: 0 baris")
        self.bupot_summary.setObjectName("mutedLabel")

        footer = QHBoxLayout()
        footer.addStretch()
        self.continue_button = QPushButton("Lanjut ke Worksheet →")
        self.continue_button.setObjectName("primaryButton")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.continue_requested.emit)
        footer.addWidget(self.continue_button)

        box.addWidget(title)
        box.addWidget(self.identity_summary)
        box.addWidget(self.sheet_summary)
        box.addWidget(self.harta_summary)
        box.addWidget(self.bupot_summary)
        box.addLayout(footer)
        return card

    def choose_worksheet(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Kertas Kerja",
            "",
            "Kertas Kerja Excel (*.xlsx *.xls);;Semua File (*.*)",
        )
        if not path:
            return

        self.worksheet_path = Path(path)
        self.worksheet_file_label.setText(self.worksheet_path.name)

        try:
            sheets = self.worksheet_importer.list_sheets(self.worksheet_path)
        except Exception as exc:
            QMessageBox.warning(self, "Kertas Kerja Tidak Dapat Dibaca", str(exc))
            return

        self.sheet_combo.clear()
        self.sheet_combo.addItems(sheets)
        suggestion = self.worksheet_importer.suggested_sheet(sheets)
        if suggestion:
            index = self.sheet_combo.findText(suggestion)
            if index >= 0:
                self.sheet_combo.setCurrentIndex(index)

        self.sheet_combo.setEnabled(bool(sheets))
        self.import_worksheet_button.setEnabled(bool(sheets))
        has_simulasi = any(str(name).strip().casefold() == "simulasi i" for name in sheets)
        self.simulasi_status.setText(
            "SIMULASI I: ✓ ditemukan" if has_simulasi else "SIMULASI I: tidak ditemukan"
        )
        self.worksheet_status.setText("Pilih sheet lalu klik Import Kertas Kerja.")

    def import_worksheet(self):
        if self.worksheet_path is None:
            return
        sheet_name = self.sheet_combo.currentText().strip()
        if not sheet_name:
            return

        result = self.worksheet_importer.parse_selected(self.worksheet_path, sheet_name)
        if result.errors:
            QMessageBox.warning(
                self,
                "Kertas Kerja Belum Valid",
                "\n".join(f"• {issue.message}" for issue in result.errors),
            )
            return

        try:
            # Bupot dipisahkan dari Kertas Kerja. Jika state lama sudah punya Bupot,
            # persist(include_bupot=False) mempertahankannya.
            self.worksheet_importer.persist(result, include_bupot=False)
        except Exception as exc:
            QMessageBox.critical(self, "Import Kertas Kerja Gagal", str(exc))
            return

        self.worksheet_result = result
        self.worksheet_status.setText(
            f"✓ {result.nama_wp or '-'} • NPWP {result.npwp} • Tahun {result.tahun_pajak} • "
            f"{len(result.harta_rows)} Harta"
        )
        self.worksheet_workbook_imported.emit(result)
        self._load_current_bupot_count()
        self._refresh_summary()

    def choose_rekap(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Rekap Bupot",
            "",
            "Rekap Bupot Excel (*.xlsx *.xls);;Semua File (*.*)",
        )
        if not path:
            return
        self.rekap_path = Path(path)
        self.rekap_label.setText(self.rekap_path.name)
        self.import_rekap_button.setEnabled(True)

    def import_rekap(self):
        if self.rekap_path is None or self.worksheet_result is None:
            QMessageBox.information(
                self,
                "Kertas Kerja Diperlukan",
                "Import Kertas Kerja terlebih dahulu agar NPWP menjadi acuan.",
            )
            return

        result = self.rekap_importer.parse(self.rekap_path)
        if not result.is_valid:
            QMessageBox.warning(self, "Rekap Bupot Belum Valid", "\n".join(result.errors))
            return

        if not self._validate_bupot_identity(result.rows):
            return

        self.rekap_importer.persist_replace(
            npwp=self.worksheet_result.npwp,
            tahun_pajak=self.worksheet_result.tahun_pajak,
            rows=result.rows,
        )
        self.bupot_count = len(result.rows)
        self.bupot_status.setText(
            f"✓ Rekap Bupot: {len(result.rows)} baris dari sheet {result.sheet_name}"
        )
        self._refresh_summary()

    def choose_single_bupot(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih PDF Bupot Satuan",
            "",
            "PDF Bupot (*.pdf);;Semua File (*.*)",
        )
        if not paths:
            return
        self.single_bupot_paths = [Path(path) for path in paths]
        names = ", ".join(path.name for path in self.single_bupot_paths[:3])
        if len(self.single_bupot_paths) > 3:
            names += f" (+{len(self.single_bupot_paths) - 3} file)"
        self.single_label.setText(names)
        self.import_single_button.setEnabled(True)

    def import_single_bupot(self):
        if not self.single_bupot_paths or self.worksheet_result is None:
            QMessageBox.information(
                self,
                "Kertas Kerja Diperlukan",
                "Import Kertas Kerja terlebih dahulu agar NPWP menjadi acuan.",
            )
            return

        rows = []
        errors = []
        for path in self.single_bupot_paths:
            try:
                rows.append(self.pdf_importer.parse(path))
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        if errors:
            QMessageBox.warning(self, "Sebagian PDF Gagal Dibaca", "\n".join(errors))
        if not rows:
            return

        if not self._validate_bupot_identity(rows):
            return

        added = self.rekap_importer.persist_merge(
            npwp=self.worksheet_result.npwp,
            tahun_pajak=self.worksheet_result.tahun_pajak,
            rows=rows,
        )
        self._load_current_bupot_count()
        self.bupot_status.setText(
            f"✓ PDF Bupot diproses: {len(rows)} file • {added} Bupot baru/unik ditambahkan"
        )
        self._refresh_summary()

    def _validate_bupot_identity(self, rows: List[WorksheetBupotRow]) -> bool:
        """Blokir hanya perbedaan WP; perbedaan tahun Bupot tetap diizinkan."""
        if self.worksheet_result is None:
            return False

        expected_npwp = "".join(ch for ch in str(self.worksheet_result.npwp) if ch.isdigit())
        expected_year = str(self.worksheet_result.tahun_pajak)

        wrong_npwp = sorted({
            row.npwp_penerima
            for row in rows
            if row.npwp_penerima
            and "".join(ch for ch in row.npwp_penerima if ch.isdigit()) != expected_npwp
        })
        wrong_year = sorted({
            str(row.tahun)
            for row in rows
            if row.tahun and str(row.tahun) != expected_year
        })

        if wrong_npwp:
            QMessageBox.warning(
                self,
                "Bupot Tidak Sesuai",
                "NPWP penerima berbeda dengan Kertas Kerja\n\n"
                "Import dibatalkan agar data antar-WP tidak tercampur.",
            )
            return False

        if wrong_year:
            years = ", ".join(wrong_year)
            QMessageBox.information(
                self,
                "Tahun Bupot Berbeda",
                f"Tahun Bupot berbeda dengan sheet Kertas Kerja ({years}).\n\n"
                "Import tetap dilanjutkan; tahun Bupot tidak dikunci ke tahun sheet Kertas Kerja.",
            )

        return True

    def _load_current_bupot_count(self):
        if self.worksheet_result is None:
            self.bupot_count = 0
            return
        state = self.rekap_importer.pph_store.load(
            self.worksheet_result.npwp,
            self.worksheet_result.tahun_pajak,
        )
        self.bupot_count = len(state.bupot_rows) if state is not None else 0

    def _refresh_summary(self):
        result = self.worksheet_result
        if result is None:
            self.identity_summary.setText("WP: -")
            self.sheet_summary.setText("Sheet: -")
            self.harta_summary.setText("Harta: 0 baris")
            self.bupot_summary.setText(f"Bupot: {self.bupot_count} baris")
            self.continue_button.setEnabled(False)
            return

        self.identity_summary.setText(
            f"WP: {result.nama_wp or '-'} • NPWP {result.npwp} • Tahun {result.tahun_pajak}"
        )
        self.sheet_summary.setText(f"Sheet: {self.sheet_combo.currentText() or '-'}")
        self.harta_summary.setText(f"Harta: {len(result.harta_rows)} baris")
        self.bupot_summary.setText(f"Bupot: {self.bupot_count} baris")
        self.continue_button.setEnabled(True)
