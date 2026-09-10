from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidgetItem

from core.worksheet_pph_state import WorksheetBupotRow, WorksheetPPhStateStore
from ui.pages.worksheet_pph_stage1 import WorksheetPage as BaseWorksheetPage
from ui.performance import suspended_updates


class WorksheetPage(BaseWorksheetPage):
    """Stage 2 Penghasilan & PPh: validasi dan persistence Bupot."""

    INVALID_BACKGROUND = QColor("#FFEBEE")
    # Detail PPh per Bupot belum menjadi kolom editable pada grid lama. Nilainya
    # tetap dibawa sebagai metadata row agar import -> edit -> save tidak
    # menghilangkan nilai yang sudah dibaca dari workbook.
    BUPOT_PPH_ROLE = Qt.UserRole + 1

    def __init__(self, parent=None):
        self.pph_state_store = WorksheetPPhStateStore()
        self._bupot_saved_rows = []
        self._bupot_restored_from_db = False
        self._bupot_last_save_error = None
        self._bupot_last_save_result = None
        super().__init__(parent)
        self._install_pph_stage2()

    def _install_pph_stage2(self):
        self.pph_identity_status = QLabel("WP belum tersambung dari preview Harta.")
        self.pph_identity_status.setObjectName("mutedLabel")
        self.pph_identity_status.setWordWrap(True)

        self.pph_validation_status = QLabel("Belum ada Bupot untuk divalidasi.")
        self.pph_validation_status.setObjectName("mutedLabel")
        self.pph_validation_status.setWordWrap(True)

        info_card = self.pph_tab.layout().itemAt(0).widget()
        if info_card is not None and info_card.layout() is not None:
            info_card.layout().addWidget(self.pph_identity_status)
            info_card.layout().addWidget(self.pph_validation_status)

        self.save_bupot_button = QPushButton("Simpan Bupot")
        self.save_bupot_button.setObjectName("primaryButton")
        self.save_bupot_button.setMinimumWidth(135)
        self.save_bupot_button.setEnabled(False)
        self.save_bupot_button.clicked.connect(self.save_bupot_changes)

        bupot_card = self.pph_tab.layout().itemAt(1).widget()
        if bupot_card is not None and bupot_card.layout() is not None:
            header_item = bupot_card.layout().itemAt(0)
            header = header_item.layout() if header_item is not None else None
            if header is not None:
                header.addWidget(self.save_bupot_button)

        self._validate_and_refresh_bupot()

    def load_harta_preview(self, pipeline_result):
        super().load_harta_preview(pipeline_result)
        self._load_pph_state_for_current_wp()

    def clear_harta_preview(self):
        super().clear_harta_preview()
        if hasattr(self, "bupot_table"):
            self._clear_bupot_working_state()

    def _current_pph_identity(self):
        result = self.harta_pipeline_result
        if result is None:
            return None, None
        npwp = self.harta_npwp or getattr(result, "npwp", None)
        year = getattr(result, "current_year", None)
        if not npwp or not year:
            return None, None
        return str(npwp), int(year)

    def _load_pph_state_for_current_wp(self):
        npwp, year = self._current_pph_identity()
        self._bupot_restored_from_db = False
        self._bupot_last_save_error = None
        self._bupot_last_save_result = None

        if not npwp or not year:
            self._clear_bupot_working_state()
            return

        nama_wp = getattr(self.harta_pipeline_result, "nama_wp", None) or "WP aktif"
        self.pph_identity_status.setText(
            f"{nama_wp} • NPWP {npwp} • Tahun Pajak {year}"
        )

        try:
            persisted = self.pph_state_store.load(npwp, year)
        except Exception as exc:
            persisted = None
            self._bupot_last_save_error = str(exc)

        if persisted is None:
            self._render_bupot_rows([])
            self._bupot_saved_rows = []
            if self._bupot_last_save_error:
                self.toast_notification.show_message(
                    "State Bupot database gagal dibaca.", "warning", 3600
                )
        else:
            self._render_bupot_rows(persisted.bupot_rows)
            self._bupot_saved_rows = list(persisted.bupot_rows)
            self._bupot_restored_from_db = True
            self.toast_notification.show_message(
                f"{len(persisted.bupot_rows)} baris Bupot dipulihkan dari database.",
                "success",
            )

        self._validate_and_refresh_bupot()

    def _clear_bupot_working_state(self):
        self._render_bupot_rows([])
        self._bupot_saved_rows = []
        self._bupot_restored_from_db = False
        self._bupot_last_save_error = None
        self._bupot_last_save_result = None
        if hasattr(self, "pph_identity_status"):
            self.pph_identity_status.setText("WP belum tersambung dari preview Harta.")
        self._validate_and_refresh_bupot()

    def _render_bupot_rows(self, rows):
        if not hasattr(self, "bupot_table"):
            return

        self._rendering_bupot = True
        with suspended_updates(self.bupot_table):
            self.bupot_table.blockSignals(True)
            try:
                self.bupot_table.clearContents()
                self.bupot_table.setRowCount(len(rows))
                for row_index, row in enumerate(rows):
                    no_item = QTableWidgetItem(str(row_index + 1))
                    no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
                    no_item.setData(
                        self.BUPOT_PPH_ROLE,
                        float(getattr(row, "pph_dipotong", 0.0) or 0.0),
                    )
                    self.bupot_table.setItem(row_index, 0, no_item)

                    text_values = (
                        row.jenis,
                        row.npwp_pemberi_kerja,
                        row.no_bupot,
                    )
                    for offset, value in enumerate(text_values, start=1):
                        self.bupot_table.setItem(
                            row_index, offset, QTableWidgetItem(str(value or ""))
                        )

                    bruto_item = QTableWidgetItem(self._format_bupot_money(row.bruto))
                    bruto_item.setData(Qt.UserRole, float(row.bruto))
                    self.bupot_table.setItem(row_index, 4, bruto_item)

                    pengurang_item = QTableWidgetItem(
                        self._format_bupot_money(row.pengurang)
                    )
                    pengurang_item.setData(Qt.UserRole, float(row.pengurang))
                    self.bupot_table.setItem(row_index, 5, pengurang_item)

                    netto_item = QTableWidgetItem(self._format_bupot_money(row.netto))
                    netto_item.setData(Qt.UserRole, float(row.netto))
                    netto_item.setFlags(netto_item.flags() & ~Qt.ItemIsEditable)
                    self.bupot_table.setItem(row_index, 6, netto_item)
            finally:
                self.bupot_table.blockSignals(False)
                self._rendering_bupot = False

        self._refresh_pph_status()
        self._refresh_bupot_actions()

    def _add_bupot_row(self):
        super()._add_bupot_row()
        row_index = self.bupot_table.rowCount() - 1
        if row_index >= 0:
            no_item = self.bupot_table.item(row_index, 0)
            if no_item is not None and no_item.data(self.BUPOT_PPH_ROLE) is None:
                no_item.setData(self.BUPOT_PPH_ROLE, 0.0)
        self._validate_and_refresh_bupot()

    def _remove_bupot_row(self):
        super()._remove_bupot_row()
        self._validate_and_refresh_bupot()

    def _on_bupot_item_changed(self, item: QTableWidgetItem):
        super()._on_bupot_item_changed(item)
        if self._rendering_bupot:
            return
        self._validate_and_refresh_bupot()

    def _row_pph_dipotong(self, row_index: int) -> float:
        no_item = self.bupot_table.item(row_index, 0)
        if no_item is None:
            return 0.0
        try:
            return float(no_item.data(self.BUPOT_PPH_ROLE) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _snapshot_bupot_rows(self):
        rows = []
        for row_index in range(self.bupot_table.rowCount()):
            rows.append(
                WorksheetBupotRow(
                    jenis=self._cell_text(row_index, 1),
                    npwp_pemberi_kerja=self.pph_state_store.normalize_npwp(
                        self._cell_text(row_index, 2)
                    ),
                    no_bupot=self._cell_text(row_index, 3),
                    bruto=self._money_value(row_index, 4),
                    pengurang=self._money_value(row_index, 5),
                    pph_dipotong=self._row_pph_dipotong(row_index),
                )
            )
        return rows

    def _cell_text(self, row: int, column: int) -> str:
        item = self.bupot_table.item(row, column)
        return " ".join(str(item.text() if item is not None else "").strip().split())

    def _validate_bupot_rows(self):
        errors = []
        seen_bupot = {}

        for row in range(self.bupot_table.rowCount()):
            jenis = self._cell_text(row, 1)
            npwp_raw = self._cell_text(row, 2)
            npwp_digits = self.pph_state_store.normalize_npwp(npwp_raw)
            no_bupot = self._cell_text(row, 3)
            bruto = self._money_value(row, 4)
            pengurang = self._money_value(row, 5)

            if not jenis:
                errors.append((row, 1, "JENIS wajib diisi."))
            if not npwp_raw:
                errors.append((row, 2, "NPWP Pemberi Kerja wajib diisi."))
            elif len(npwp_digits) not in {15, 16} or any(
                ch not in "0123456789.- " for ch in npwp_raw
            ):
                errors.append((row, 2, "NPWP harus berisi 15 atau 16 digit."))
            if not no_bupot:
                errors.append((row, 3, "NO BUPOT wajib diisi."))
            if bruto < 0:
                errors.append((row, 4, "BRUTO tidak boleh negatif."))
            if pengurang < 0:
                errors.append((row, 5, "PENGURANG tidak boleh negatif."))

            if no_bupot:
                key = no_bupot.casefold()
                if key in seen_bupot:
                    first_row = seen_bupot[key]
                    errors.append((first_row, 3, "NO BUPOT duplikat."))
                    errors.append((row, 3, "NO BUPOT duplikat."))
                else:
                    seen_bupot[key] = row

        return errors

    def _apply_bupot_validation(self, errors):
        error_map = {}
        for row, column, message in errors:
            error_map.setdefault((row, column), message)

        self.bupot_table.blockSignals(True)
        try:
            for row in range(self.bupot_table.rowCount()):
                for column in range(1, 6):
                    item = self.bupot_table.item(row, column)
                    if item is None:
                        continue
                    message = error_map.get((row, column))
                    if message:
                        item.setBackground(self.INVALID_BACKGROUND)
                        item.setToolTip(message)
                    else:
                        item.setData(Qt.BackgroundRole, None)
                        item.setToolTip("")
        finally:
            self.bupot_table.blockSignals(False)

    def _validate_and_refresh_bupot(self):
        if not hasattr(self, "bupot_table"):
            return []

        errors = self._validate_bupot_rows()
        self._apply_bupot_validation(errors)

        if hasattr(self, "pph_validation_status"):
            if not self.bupot_table.rowCount():
                self.pph_validation_status.setText(
                    "Belum ada Bupot. Tambahkan baris untuk mulai input manual."
                )
                self.pph_validation_status.setStyleSheet("color:#486581;")
            elif errors:
                self.pph_validation_status.setText(
                    f"⚠ {len(errors)} masalah validasi ditemukan. Sel bermasalah ditandai merah."
                )
                self.pph_validation_status.setStyleSheet("color:#B71C1C; font-weight:600;")
            else:
                self.pph_validation_status.setText(
                    "✓ Semua baris Bupot valid dan siap disimpan."
                )
                self.pph_validation_status.setStyleSheet("color:#1B5E20; font-weight:600;")

        self._refresh_pph_status()
        self._refresh_bupot_actions()
        return errors

    def _has_unsaved_bupot_changes(self):
        return self._snapshot_bupot_rows() != self._bupot_saved_rows

    def _refresh_bupot_actions(self):
        super()._refresh_bupot_actions()
        if not hasattr(self, "save_bupot_button"):
            return

        npwp, year = self._current_pph_identity()
        errors = self._validate_bupot_rows()
        self.save_bupot_button.setEnabled(
            bool(npwp and year)
            and not errors
            and self._has_unsaved_bupot_changes()
        )

    def save_bupot_changes(self):
        npwp, year = self._current_pph_identity()
        if not npwp or not year:
            self.toast_notification.show_message(
                "Preview WP belum tersedia. Muat data Coretax terlebih dahulu.",
                "warning",
                3600,
            )
            return None

        errors = self._validate_and_refresh_bupot()
        if errors:
            self.toast_notification.show_message(
                "Bupot belum dapat disimpan karena masih ada data tidak valid.",
                "warning",
                3600,
            )
            return None

        rows = self._snapshot_bupot_rows()
        self._bupot_last_save_error = None
        self._bupot_last_save_result = None
        try:
            self._bupot_last_save_result = self.pph_state_store.save(
                npwp=npwp,
                tahun_pajak=year,
                bupot_rows=rows,
            )
        except Exception as exc:
            self._bupot_last_save_error = str(exc)
            self.toast_notification.show_message(
                "Bupot gagal disimpan ke database.", "error", 3600
            )
            return None

        self._bupot_saved_rows = list(rows)
        self._refresh_bupot_actions()
        self.pph_validation_status.setText(
            f"✓ {len(rows)} baris Bupot tersimpan ke database untuk Tahun Pajak {year}."
        )
        self.pph_validation_status.setStyleSheet("color:#1B5E20; font-weight:600;")
        self.toast_notification.show_message(
            f"{len(rows)} baris Bupot tersimpan ke database.", "success"
        )
        return self._bupot_last_save_result
