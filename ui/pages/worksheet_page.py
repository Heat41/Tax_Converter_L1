from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class WorksheetPage(QWidget):
    """Halaman worksheet utama.

    Tab Harta menerima hasil pipeline SIMULASI I dari halaman Impor Coretax.
    Original Import selalu read-only, sedangkan Edited / Current dapat dikoreksi
    tanpa mengubah hasil import awal. Tab Penghasilan & PPh tetap terpisah.
    """

    HARTA_FIELDS = (
        "nomor",
        "kode_eform",
        "kode_ct",
        "nama_harta",
        "nomor_akun_keterangan",
        "atas_nama",
        "nama_bank",
        "tahun_perolehan",
        "nilai_tahun_sebelumnya",
        "nilai_tahun_berjalan",
    )
    NUMERIC_COLUMNS = {8, 9}
    YEAR_COLUMN = 7
    CHANGE_BACKGROUND = QColor("#FFF3CD")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.harta_pipeline_result = None
        self.harta_original_rows = []
        self.harta_current_rows = []
        self.harta_saved_rows = []
        self.harta_mode = "original"
        self._rendering_harta = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Worksheet")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Periksa hasil Harta L-1 dan lengkapi data penghasilan serta PPh Tahunan."
        )
        subtitle.setObjectName("pageSubTitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("worksheetTabs")
        self.tabs.setDocumentMode(True)

        self.harta_tab = self._build_harta_tab()
        self.pph_tab = self._build_pph_tab()

        self.tabs.addTab(self.harta_tab, "Harta / SIMULASI I")
        self.tabs.addTab(self.pph_tab, "Penghasilan & PPh 2025")

        layout.addWidget(self.tabs, 1)

    def _build_harta_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        heading = QLabel("Worksheet Harta — SIMULASI I")
        heading.setObjectName("sectionTitle")
        description = QLabel(
            "Original Import menyimpan hasil awal pipeline dan tidak dapat diedit. "
            "Gunakan Edited / Current untuk koreksi manual; sel yang berubah akan "
            "ditandai agar perbedaannya mudah diaudit."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)

        self.harta_status = QLabel("Belum ada preview Harta dari halaman Impor Coretax.")
        self.harta_status.setObjectName("mutedLabel")
        self.harta_status.setWordWrap(True)

        info_layout.addWidget(heading)
        info_layout.addWidget(description)
        info_layout.addWidget(self.harta_status)
        layout.addWidget(info_card)

        toolbar = QHBoxLayout()
        self.original_button = QPushButton("Original Import")
        self.original_button.setObjectName("secondaryButton")
        self.current_button = QPushButton("Edited / Current")
        self.current_button.setObjectName("secondaryButton")
        self.reset_harta_button = QPushButton("Reset ke Import")
        self.reset_harta_button.setObjectName("secondaryButton")
        self.reset_harta_button.setEnabled(False)
        self.save_harta_button = QPushButton("Simpan Perubahan")
        self.save_harta_button.setObjectName("primaryButton")
        self.save_harta_button.setEnabled(False)

        self.original_button.clicked.connect(
            lambda: self._show_harta_mode("original")
        )
        self.current_button.clicked.connect(
            lambda: self._show_harta_mode("current")
        )
        self.reset_harta_button.clicked.connect(self.reset_harta_to_import)
        self.save_harta_button.clicked.connect(self.save_harta_changes)

        toolbar.addWidget(self.original_button)
        toolbar.addWidget(self.current_button)
        toolbar.addWidget(self.reset_harta_button)
        toolbar.addStretch()
        toolbar.addWidget(self.save_harta_button)
        layout.addLayout(toolbar)

        self.harta_table = QTableWidget(0, 10)
        self.harta_table.setHorizontalHeaderLabels([
            "NO",
            "KODE EFORM",
            "KODE CT",
            "NAMA HARTA",
            "NOMOR AKUN / KETERANGAN",
            "ATAS NAMA",
            "NAMA BANK",
            "TH PEROLEHAN",
            "TAHUN SEBELUMNYA",
            "TAHUN BERJALAN",
        ])
        self.harta_table.setAlternatingRowColors(True)
        self.harta_table.verticalHeader().setVisible(False)
        self.harta_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.harta_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.harta_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.harta_table.horizontalHeader().setMinimumSectionSize(80)
        self.harta_table.itemChanged.connect(self._on_harta_item_changed)
        layout.addWidget(self.harta_table, 1)

        return page

    def load_harta_preview(self, pipeline_result):
        """Terima hasil preview dari halaman Impor Coretax."""
        if pipeline_result is None or not getattr(
            pipeline_result, "worksheet_rows", None
        ):
            self.clear_harta_preview()
            return

        self.harta_pipeline_result = pipeline_result
        self.harta_original_rows = list(pipeline_result.worksheet_rows)
        self.harta_current_rows = list(pipeline_result.worksheet_rows)
        self.harta_saved_rows = list(pipeline_result.worksheet_rows)
        self.harta_mode = "original"

        year = pipeline_result.current_year or "-"
        skipped = getattr(pipeline_result.mapping, "skipped_rows", 0)
        self.harta_status.setText(
            f"{len(self.harta_original_rows)} baris Harta tersambung • "
            f"Tahun {year} • {skipped} baris dilewati • Mode Original Import"
        )
        self._render_harta_rows(self.harta_original_rows)
        self._refresh_harta_actions()

    def clear_harta_preview(self):
        self.harta_pipeline_result = None
        self.harta_original_rows = []
        self.harta_current_rows = []
        self.harta_saved_rows = []
        self.harta_mode = "original"
        self._rendering_harta = True
        try:
            self.harta_table.clearContents()
            self.harta_table.setRowCount(0)
        finally:
            self._rendering_harta = False
        self.harta_status.setText(
            "Belum ada preview Harta dari halaman Impor Coretax."
        )
        self._refresh_harta_actions()

    def _show_harta_mode(self, mode: str):
        if mode not in {"original", "current"}:
            return
        self.harta_mode = mode
        rows = (
            self.harta_original_rows
            if mode == "original"
            else self.harta_current_rows
        )
        self._render_harta_rows(rows)

        if self.harta_pipeline_result is not None:
            self._update_harta_status()
        self._refresh_harta_actions()

    def _render_harta_rows(self, rows):
        self._rendering_harta = True
        self.harta_table.blockSignals(True)
        try:
            self.harta_table.clearContents()
            self.harta_table.setRowCount(len(rows))

            for row_index, item in enumerate(rows):
                values = [getattr(item, field) for field in self.HARTA_FIELDS]
                for column_index, value in enumerate(values):
                    table_item = QTableWidgetItem(
                        self._format_harta_value(
                            value,
                            numeric=column_index in self.NUMERIC_COLUMNS,
                        )
                    )
                    if self.harta_mode == "original" or column_index == 0:
                        table_item.setFlags(
                            table_item.flags() & ~Qt.ItemIsEditable
                        )
                    self.harta_table.setItem(
                        row_index,
                        column_index,
                        table_item,
                    )
                    if self.harta_mode == "current":
                        self._apply_change_highlight(
                            row_index,
                            column_index,
                            table_item,
                        )
        finally:
            self.harta_table.blockSignals(False)
            self._rendering_harta = False

        if self.harta_mode == "current" and rows:
            self.harta_table.setEditTriggers(
                QTableWidget.DoubleClicked
                | QTableWidget.EditKeyPressed
                | QTableWidget.SelectedClicked
            )
        else:
            self.harta_table.setEditTriggers(QTableWidget.NoEditTriggers)

    def _on_harta_item_changed(self, item: QTableWidgetItem):
        if self._rendering_harta or self.harta_mode != "current":
            return

        row_index = item.row()
        column_index = item.column()
        if (
            row_index < 0
            or row_index >= len(self.harta_current_rows)
            or column_index <= 0
            or column_index >= len(self.HARTA_FIELDS)
        ):
            return

        field_name = self.HARTA_FIELDS[column_index]
        old_row = self.harta_current_rows[row_index]

        try:
            value = self._parse_harta_edit(item.text(), column_index)
        except ValueError:
            original_value = getattr(old_row, field_name)
            self.harta_table.blockSignals(True)
            try:
                item.setText(
                    self._format_harta_value(
                        original_value,
                        numeric=column_index in self.NUMERIC_COLUMNS,
                    )
                )
            finally:
                self.harta_table.blockSignals(False)
            self.harta_status.setText(
                "Nilai tidak valid. TH PEROLEHAN harus berupa tahun, dan kolom nilai harus berupa angka."
            )
            return

        self.harta_current_rows[row_index] = replace(
            old_row,
            **{field_name: value},
        )

        # Normalisasikan tampilan angka setelah edit.
        if column_index in self.NUMERIC_COLUMNS or column_index == self.YEAR_COLUMN:
            self.harta_table.blockSignals(True)
            try:
                item.setText(
                    self._format_harta_value(
                        value,
                        numeric=column_index in self.NUMERIC_COLUMNS,
                    )
                )
            finally:
                self.harta_table.blockSignals(False)

        self._apply_change_highlight(row_index, column_index, item)
        self._refresh_harta_actions()
        self._update_harta_status()

    def _apply_change_highlight(
        self,
        row_index: int,
        column_index: int,
        table_item: QTableWidgetItem,
    ) -> None:
        changed = self._cell_changed_from_original(row_index, column_index)
        if changed:
            table_item.setBackground(self.CHANGE_BACKGROUND)
        else:
            table_item.setData(Qt.BackgroundRole, None)

    def _cell_changed_from_original(self, row_index: int, column_index: int) -> bool:
        if (
            row_index >= len(self.harta_original_rows)
            or row_index >= len(self.harta_current_rows)
        ):
            return False
        field_name = self.HARTA_FIELDS[column_index]
        return getattr(
            self.harta_original_rows[row_index], field_name
        ) != getattr(self.harta_current_rows[row_index], field_name)

    def _count_changed_cells(self) -> int:
        total = 0
        common_rows = min(
            len(self.harta_original_rows),
            len(self.harta_current_rows),
        )
        for row_index in range(common_rows):
            for column_index in range(1, len(self.HARTA_FIELDS)):
                if self._cell_changed_from_original(row_index, column_index):
                    total += 1
        return total

    def _has_unsaved_harta_changes(self) -> bool:
        return self.harta_current_rows != self.harta_saved_rows

    def _refresh_harta_actions(self):
        has_data = bool(self.harta_current_rows)
        changed_cells = self._count_changed_cells()
        self.reset_harta_button.setEnabled(has_data and changed_cells > 0)
        self.save_harta_button.setEnabled(
            has_data
            and self.harta_mode == "current"
            and self._has_unsaved_harta_changes()
        )

    def _update_harta_status(self, *, saved: bool = False):
        if self.harta_pipeline_result is None:
            return
        year = self.harta_pipeline_result.current_year or "-"
        label = (
            "Original Import"
            if self.harta_mode == "original"
            else "Edited / Current"
        )
        changed_cells = self._count_changed_cells()
        suffix = ""
        if self.harta_mode == "current":
            if saved:
                suffix = " • perubahan tersimpan pada sesi worksheet"
            elif self._has_unsaved_harta_changes():
                suffix = " • ada perubahan belum disimpan"
            elif changed_cells:
                suffix = " • koreksi tersimpan pada sesi worksheet"
        self.harta_status.setText(
            f"Mode {label} • {len(self.harta_current_rows)} baris Harta • "
            f"Tahun {year} • {changed_cells} sel dikoreksi{suffix}"
        )

    def save_harta_changes(self):
        if self.harta_mode != "current" or not self.harta_current_rows:
            return
        self.harta_saved_rows = list(self.harta_current_rows)
        self._refresh_harta_actions()
        self._update_harta_status(saved=True)

    def reset_harta_to_import(self):
        if not self.harta_original_rows:
            return
        self.harta_current_rows = list(self.harta_original_rows)
        self._render_harta_rows(self.harta_current_rows)
        self._refresh_harta_actions()
        self._update_harta_status()

    @classmethod
    def _parse_harta_edit(cls, text: str, column_index: int):
        value = str(text or "").strip()
        if column_index == cls.YEAR_COLUMN:
            if not value:
                raise ValueError("tahun kosong")
            try:
                year = int(float(value.replace(",", ".")))
            except ValueError as exc:
                raise ValueError("tahun tidak valid") from exc
            if year < 1900 or year > 2100:
                raise ValueError("tahun di luar rentang")
            return year

        if column_index in cls.NUMERIC_COLUMNS:
            if not value:
                return 0.0
            cleaned = value.replace("Rp", "").replace("rp", "").replace(" ", "")
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "." in cleaned:
                parts = cleaned.split(".")
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    cleaned = "".join(parts)
            elif "," in cleaned:
                tail = cleaned.rsplit(",", 1)[-1]
                cleaned = (
                    cleaned.replace(",", ".")
                    if len(tail) <= 2
                    else cleaned.replace(",", "")
                )
            try:
                return float(cleaned)
            except ValueError as exc:
                raise ValueError("angka tidak valid") from exc

        return value

    @staticmethod
    def _format_harta_value(value, *, numeric: bool = False) -> str:
        if value is None:
            return ""
        if numeric:
            try:
                number = float(value)
                if number == 0:
                    return "0"
                return f"{number:,.0f}".replace(",", ".")
            except (TypeError, ValueError):
                pass
        return str(value)

    def _build_pph_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        heading = QLabel("Worksheet Penghasilan & PPh 2025")
        heading.setObjectName("sectionTitle")
        description = QLabel(
            "Bagian ini disiapkan untuk input manual Bupot dan komponen penghasilan. "
            "Data Harta L-1 tetap diproses terpisah melalui SIMULASI I."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)

        info_layout.addWidget(heading)
        info_layout.addWidget(description)
        layout.addWidget(info_card)

        bupot_card = QFrame(objectName="card")
        bupot_layout = QVBoxLayout(bupot_card)
        bupot_layout.setContentsMargins(20, 18, 20, 18)
        bupot_layout.setSpacing(10)

        header = QHBoxLayout()
        bupot_title = QLabel("Bukti Potong — Input Manual")
        bupot_title.setObjectName("sectionTitle")
        self.add_bupot_button = QPushButton("+ Tambah Baris")
        self.add_bupot_button.setObjectName("secondaryButton")
        self.remove_bupot_button = QPushButton("Hapus Baris")
        self.remove_bupot_button.setObjectName("secondaryButton")
        self.add_bupot_button.clicked.connect(self._add_bupot_row)
        self.remove_bupot_button.clicked.connect(self._remove_bupot_row)

        header.addWidget(bupot_title)
        header.addStretch()
        header.addWidget(self.add_bupot_button)
        header.addWidget(self.remove_bupot_button)
        bupot_layout.addLayout(header)

        self.bupot_table = QTableWidget(0, 7)
        self.bupot_table.setHorizontalHeaderLabels([
            "NO",
            "JENIS",
            "NPWP PEMBERI KERJA",
            "NO BUPOT",
            "BRUTO",
            "PENGURANG",
            "NETTO",
        ])
        self.bupot_table.setAlternatingRowColors(True)
        self.bupot_table.verticalHeader().setVisible(False)
        self.bupot_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bupot_table.setMinimumHeight(220)
        bupot_layout.addWidget(self.bupot_table)
        layout.addWidget(bupot_card)

        summary_card = QFrame(objectName="card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 18, 20, 18)
        summary_layout.setSpacing(6)

        summary_title = QLabel("Ringkasan Perhitungan")
        summary_title.setObjectName("sectionTitle")
        summary_note = QLabel(
            "UMKM, penghasilan lainnya, pengurang penghasilan neto, PTKP, PPh terutang, "
            "angsuran PPh 25, dan kurang/lebih bayar akan ditambahkan setelah struktur Bupot selesai."
        )
        summary_note.setObjectName("pageSubTitle")
        summary_note.setWordWrap(True)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(summary_note)
        layout.addWidget(summary_card)
        layout.addStretch()

        return page

    def _add_bupot_row(self):
        row = self.bupot_table.rowCount()
        self.bupot_table.insertRow(row)
        no_item = QTableWidgetItem(str(row + 1))
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        self.bupot_table.setItem(row, 0, no_item)

        netto_item = QTableWidgetItem("0")
        netto_item.setFlags(netto_item.flags() & ~Qt.ItemIsEditable)
        self.bupot_table.setItem(row, 6, netto_item)

    def _remove_bupot_row(self):
        selected = sorted(
            {index.row() for index in self.bupot_table.selectedIndexes()},
            reverse=True,
        )
        if not selected and self.bupot_table.rowCount() > 0:
            selected = [self.bupot_table.rowCount() - 1]

        for row in selected:
            self.bupot_table.removeRow(row)

        for row in range(self.bupot_table.rowCount()):
            item = self.bupot_table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.bupot_table.setItem(row, 0, item)
            item.setText(str(row + 1))
