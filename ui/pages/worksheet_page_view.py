import json
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.pages.worksheet_harta_structure import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_table_interaction, suspended_updates


class WorksheetPage(BaseWorksheetPage):
    """Presentation wrapper untuk mode, notifikasi, performa, dan audit Worksheet Harta."""

    NOTICE_STYLES = {
        "info": (
            "background:#EAF4FD; color:#0D47A1; border:1px solid #90CAF9; "
            "border-radius:7px; padding:8px 12px; font-weight:600;"
        ),
        "warning": (
            "background:#FFF8E1; color:#8A5A00; border:1px solid #FFE082; "
            "border-radius:7px; padding:8px 12px; font-weight:600;"
        ),
        "success": (
            "background:#E8F5E9; color:#1B5E20; border:1px solid #A5D6A7; "
            "border-radius:7px; padding:8px 12px; font-weight:600;"
        ),
        "error": (
            "background:#FFEBEE; color:#B71C1C; border:1px solid #EF9A9A; "
            "border-radius:7px; padding:8px 12px; font-weight:600;"
        ),
    }

    HARTA_COLUMN_WIDTHS = {
        0: 55,
        1: 95,
        2: 85,
        3: 230,
        4: 235,
        5: 155,
        6: 145,
        7: 105,
        8: 135,
        9: 135,
    }

    AUDIT_COLUMN_WIDTHS = {
        0: 145,
        1: 80,
        2: 65,
        3: 175,
        4: 280,
        5: 280,
    }

    AUDIT_FIELD_LABELS = {
        "__row__": "Baris Harta",
        "kode_eform": "Kode EFORM",
        "kode_ct": "Kode CT",
        "nama_harta": "Nama Harta",
        "nomor_akun_keterangan": "Nomor Akun / Keterangan",
        "atas_nama": "Atas Nama",
        "nama_bank": "Nama Bank",
        "tahun_perolehan": "Tahun Perolehan",
        "nilai_tahun_sebelumnya": "Tahun Sebelumnya",
        "nilai_tahun_berjalan": "Tahun Berjalan",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audit_rows = []
        self._install_harta_feedback()
        self._install_responsive_harta_toolbar()
        self._optimize_harta_table()
        self._install_audit_tab()

    def _install_harta_feedback(self):
        status_font = self.harta_status.font()
        status_font.setBold(True)
        self.harta_status.setFont(status_font)
        self.harta_status.setStyleSheet("color:#102A43; font-weight:700;")

        self.harta_notice = QLabel()
        self.harta_notice.setWordWrap(True)
        self.harta_notice.setVisible(False)

        info_card = self.harta_status.parentWidget()
        if info_card is not None and info_card.layout() is not None:
            info_card.layout().addWidget(self.harta_notice)

        try:
            self.reset_harta_button.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.reset_harta_button.clicked.connect(self._confirm_reset_harta_to_import)

    def _install_responsive_harta_toolbar(self):
        """Ubah toolbar menjadi dua baris agar teks tombol tidak terpotong di windowed mode."""
        page_layout = self.harta_tab.layout()
        if page_layout is None or page_layout.count() < 2:
            return

        toolbar_item = page_layout.takeAt(1)
        old_toolbar = toolbar_item.layout() if toolbar_item is not None else None

        buttons = (
            self.original_button,
            self.current_button,
            self.add_harta_button,
            self.remove_harta_button,
            self.reset_harta_button,
            self.save_harta_button,
        )
        if old_toolbar is not None:
            for button in buttons:
                old_toolbar.removeWidget(button)
            old_toolbar.deleteLater()

        self.harta_action_bar = QWidget()
        self.harta_action_grid = QGridLayout(self.harta_action_bar)
        self.harta_action_grid.setContentsMargins(0, 0, 0, 0)
        self.harta_action_grid.setHorizontalSpacing(10)
        self.harta_action_grid.setVerticalSpacing(8)

        for button in buttons:
            button.setMinimumWidth(135)
            button.setMinimumHeight(40)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.harta_action_grid.addWidget(self.original_button, 0, 0)
        self.harta_action_grid.addWidget(self.current_button, 0, 1)
        self.harta_action_grid.addWidget(self.reset_harta_button, 0, 2)
        self.harta_action_grid.addWidget(self.add_harta_button, 1, 0)
        self.harta_action_grid.addWidget(self.remove_harta_button, 1, 1)
        self.harta_action_grid.addWidget(self.save_harta_button, 1, 2)

        for column in range(3):
            self.harta_action_grid.setColumnStretch(column, 1)

        page_layout.insertWidget(1, self.harta_action_bar)

    def _optimize_harta_table(self):
        """Kurangi layout recalculation agar scroll/resize window lebih halus."""
        optimize_table_interaction(
            self.harta_table,
            column_widths=self.HARTA_COLUMN_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )

    def _install_audit_tab(self):
        self.audit_tab = QWidget()
        layout = QVBoxLayout(self.audit_tab)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        title = QLabel("Riwayat Audit — Worksheet Harta")
        title.setObjectName("sectionTitle")
        description = QLabel(
            "Menampilkan perubahan yang sudah tersimpan ke database. "
            "EDIT dicatat per kolom, sedangkan ADD dan DELETE dicatat per baris."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)

        self.audit_summary = QLabel("Belum ada riwayat audit untuk ditampilkan.")
        self.audit_summary.setObjectName("mutedLabel")
        self.audit_summary.setWordWrap(True)

        info_layout.addWidget(title)
        info_layout.addWidget(description)
        info_layout.addWidget(self.audit_summary)
        layout.addWidget(info_card)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        filter_label = QLabel("Tampilkan:")
        self.audit_filter = QComboBox()
        self.audit_filter.addItems(["Semua Aksi", "ADD", "EDIT", "DELETE"])
        self.audit_filter.setMinimumWidth(150)
        self.audit_filter.currentTextChanged.connect(
            lambda _text: self._render_audit_rows()
        )

        self.audit_refresh_button = QPushButton("Refresh Riwayat")
        self.audit_refresh_button.setObjectName("secondaryButton")
        self.audit_refresh_button.setMinimumWidth(145)
        self.audit_refresh_button.clicked.connect(self._refresh_audit_history)

        controls.addWidget(filter_label)
        controls.addWidget(self.audit_filter)
        controls.addStretch()
        controls.addWidget(self.audit_refresh_button)
        layout.addLayout(controls)

        self.audit_table = QTableWidget(0, 6)
        self.audit_table.setHorizontalHeaderLabels([
            "WAKTU",
            "AKSI",
            "BARIS",
            "KOLOM",
            "NILAI LAMA",
            "NILAI BARU",
        ])
        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.verticalHeader().setVisible(False)
        self.audit_table.setMinimumHeight(320)
        self.audit_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        optimize_table_interaction(
            self.audit_table,
            column_widths=self.AUDIT_COLUMN_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        layout.addWidget(self.audit_table, 1)

        self.tabs.addTab(self.audit_tab, "Riwayat Audit")

    def _show_notice(self, message: str, level: str = "info"):
        self.harta_notice.setText(message)
        self.harta_notice.setStyleSheet(
            self.NOTICE_STYLES.get(level, self.NOTICE_STYLES["info"])
        )
        self.harta_notice.setVisible(True)

    def _hide_notice(self):
        self.harta_notice.clear()
        self.harta_notice.setVisible(False)

    def _change_summary(self) -> str:
        return (
            f"{self._count_changed_cells()} sel dikoreksi, "
            f"{self._count_added_rows()} baris ditambah, "
            f"{self._count_deleted_rows()} baris dihapus"
        )

    def load_harta_preview(self, pipeline_result):
        super().load_harta_preview(pipeline_result)
        if pipeline_result is not None and getattr(pipeline_result, "worksheet_rows", None):
            if self.harta_restored_from_db:
                self._show_notice(
                    "✓ Data Harta tersambung. Draft Edited / Current yang sebelumnya tersimpan di database ditemukan dan telah dipulihkan.",
                    "success",
                )
            elif self.last_harta_save_error:
                self._show_notice(
                    f"⚠ Data Harta tersambung, tetapi draft database tidak dapat dibaca: {self.last_harta_save_error}",
                    "warning",
                )
            else:
                self._show_notice(
                    "✓ Data Harta berhasil tersambung. Mode Original Import aktif dan data hanya dapat dilihat.",
                    "info",
                )
            self._refresh_audit_history()
        else:
            self._hide_notice()
            self._clear_audit_history()

    def clear_harta_preview(self):
        super().clear_harta_preview()
        if hasattr(self, "harta_notice"):
            self._hide_notice()
        if hasattr(self, "audit_table"):
            self._clear_audit_history()

    def _show_harta_mode(self, mode: str):
        super()._show_harta_mode(mode)
        if self.harta_pipeline_result is None:
            return

        if mode == "original":
            self._show_notice(
                "MODE ORIGINAL IMPORT — data asli hasil Coretax, read-only dan tidak dapat dikoreksi.",
                "info",
            )
        elif mode == "current":
            if self._has_unsaved_harta_changes():
                self._show_notice(
                    f"⚠ MODE EDITED / CURRENT — {self._change_summary()} dan belum disimpan.",
                    "warning",
                )
            elif self.harta_restored_from_db and self._has_any_harta_changes():
                self._show_notice(
                    f"✓ MODE EDITED / CURRENT — draft database dipulihkan. {self._change_summary()} terhadap Original Import.",
                    "success",
                )
            else:
                self._show_notice(
                    "MODE EDITED / CURRENT — klik dua kali pada sel untuk koreksi, atau gunakan Tambah/Hapus Baris.",
                    "info",
                )

    def _on_harta_item_changed(self, item):
        before = self._has_unsaved_harta_changes()
        super()._on_harta_item_changed(item)
        after = self._has_unsaved_harta_changes()

        if self.harta_mode == "current" and after:
            self._show_notice(
                f"⚠ {self._change_summary()} dan belum disimpan.",
                "warning",
            )
        elif before and not after:
            self._show_notice(
                "MODE EDITED / CURRENT — tidak ada perubahan yang belum disimpan.",
                "info",
            )

    def add_harta_row(self):
        before = len(self.harta_current_rows)
        super().add_harta_row()
        if len(self.harta_current_rows) > before:
            self._show_notice(
                f"⚠ Baris Harta manual baru ditambahkan. {self._change_summary()} dan belum disimpan.",
                "warning",
            )

    def remove_selected_harta_rows(self):
        if self.harta_mode != "current":
            return 0

        selected_rows = sorted(
            {index.row() for index in self.harta_table.selectedIndexes()}
        )
        if not selected_rows:
            self._show_notice(
                "Pilih satu atau beberapa baris Harta yang akan dihapus.",
                "warning",
            )
            return 0

        answer = QMessageBox.question(
            self,
            "Hapus Baris Harta",
            f"Hapus {len(selected_rows)} baris yang dipilih dari Edited / Current?\n\n"
            "Original Import tidak akan berubah dan baris dapat dipulihkan dengan Reset ke Import.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return 0

        removed = super().remove_selected_harta_rows()
        if removed:
            self._show_notice(
                f"⚠ {removed} baris dihapus dari Edited / Current. {self._change_summary()} dan belum disimpan.",
                "warning",
            )
        return removed

    def save_harta_changes(self):
        had_unsaved = self._has_unsaved_harta_changes()
        result = super().save_harta_changes()
        if not had_unsaved:
            return result

        if self.last_harta_save_error:
            self._show_notice(
                f"✕ Perubahan belum tersimpan ke database: {self.last_harta_save_error}",
                "error",
            )
            return result

        if result is not None and getattr(result, "persisted", False):
            self._show_notice(
                "✓ Perubahan tersimpan ke database. "
                f"Audit baru: {result.audit_count} catatan "
                f"({result.add_count} ADD, {result.edit_count} EDIT, {result.delete_count} DELETE). "
                f"{self._change_summary()} tetap ditandai terhadap Original Import.",
                "success",
            )
            self._refresh_audit_history()
        else:
            self._show_notice(
                f"✓ Perubahan tersimpan pada sesi worksheet. {self._change_summary()} tetap ditandai terhadap Original Import.",
                "success",
            )
        return result

    def _confirm_reset_harta_to_import(self):
        if not self.harta_original_rows or not self._has_any_harta_changes():
            return

        answer = QMessageBox.question(
            self,
            "Reset ke Original Import",
            "Semua koreksi, baris tambahan, dan penghapusan pada Edited / Current akan dibatalkan dan dikembalikan persis ke hasil import Coretax.\n\n"
            "Original Import tidak akan berubah. Lanjutkan reset?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.reset_harta_to_import()

    def reset_harta_to_import(self):
        super().reset_harta_to_import()
        self._show_notice(
            "✓ Edited / Current sudah dikembalikan ke Original Import pada layar. Klik Simpan Perubahan untuk menyimpan reset ini ke database.",
            "success",
        )

    def _current_audit_state_id(self):
        result = self.last_harta_save_result
        if result is not None and getattr(result, "persisted", False):
            return int(result.state_id)

        if (
            not self.harta_npwp
            or self.harta_pipeline_result is None
            or not self.harta_original_rows
        ):
            return None

        year = getattr(self.harta_pipeline_result, "current_year", None)
        if not year:
            return None

        persisted = self.harta_state_store.load_matching(
            self.harta_npwp,
            int(year),
            self.harta_original_rows,
        )
        return int(persisted.id) if persisted is not None else None

    def _refresh_audit_history(self):
        if not hasattr(self, "audit_table"):
            return

        try:
            state_id = self._current_audit_state_id()
            if state_id is None:
                self._audit_rows = []
                self.audit_summary.setText(
                    "Belum ada perubahan Worksheet Harta yang tersimpan ke database."
                )
                self._render_audit_rows()
                return

            self._audit_rows = [
                dict(row) for row in self.harta_state_store.get_audit_rows(state_id)
            ]
            add_count = sum(row.get("action") == "ADD" for row in self._audit_rows)
            edit_count = sum(row.get("action") == "EDIT" for row in self._audit_rows)
            delete_count = sum(
                row.get("action") == "DELETE" for row in self._audit_rows
            )
            self.audit_summary.setText(
                f"{len(self._audit_rows)} catatan tersimpan di database • "
                f"{add_count} ADD • {edit_count} EDIT • {delete_count} DELETE"
            )
            self._render_audit_rows()
        except Exception as exc:
            self._audit_rows = []
            self.audit_summary.setText(f"Gagal membaca riwayat audit: {exc}")
            self._render_audit_rows()

    def _clear_audit_history(self):
        self._audit_rows = []
        if hasattr(self, "audit_summary"):
            self.audit_summary.setText("Belum ada riwayat audit untuk ditampilkan.")
        if hasattr(self, "audit_table"):
            with suspended_updates(self.audit_table):
                self.audit_table.clearContents()
                self.audit_table.setRowCount(0)

    def _render_audit_rows(self):
        if not hasattr(self, "audit_table"):
            return

        selected_action = self.audit_filter.currentText()
        rows = self._audit_rows
        if selected_action != "Semua Aksi":
            rows = [row for row in rows if row.get("action") == selected_action]

        with suspended_updates(self.audit_table):
            self.audit_table.blockSignals(True)
            try:
                self.audit_table.clearContents()
                self.audit_table.setRowCount(len(rows))
                for row_index, row in enumerate(rows):
                    values = (
                        self._format_audit_time(row.get("waktu_perubahan")),
                        row.get("action") or "-",
                        row.get("row_order") or "-",
                        self.AUDIT_FIELD_LABELS.get(
                            row.get("nama_kolom"), row.get("nama_kolom") or "-"
                        ),
                        self._format_audit_value(
                            row.get("nilai_lama"), row.get("nama_kolom")
                        ),
                        self._format_audit_value(
                            row.get("nilai_baru"), row.get("nama_kolom")
                        ),
                    )
                    for column_index, value in enumerate(values):
                        item = QTableWidgetItem(str(value))
                        item.setToolTip(str(value))
                        self.audit_table.setItem(row_index, column_index, item)
            finally:
                self.audit_table.blockSignals(False)

    @staticmethod
    def _format_audit_time(value):
        text = str(value or "").strip()
        if not text:
            return "-"
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            return parsed.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return text

    @classmethod
    def _format_audit_value(cls, value, field_name):
        if value is None or value == "":
            return "-"
        text = str(value)

        if field_name == "__row__":
            try:
                row = json.loads(text)
            except (TypeError, ValueError, json.JSONDecodeError):
                return text
            kode = row.get("kode_ct") or row.get("kode_eform") or "-"
            nama = row.get("nama_harta") or "Harta"
            nilai = row.get("nilai_tahun_berjalan")
            if nilai is not None:
                try:
                    nilai_text = f"{float(nilai):,.0f}".replace(",", ".")
                    return f"{kode} • {nama} • {nilai_text}"
                except (TypeError, ValueError):
                    pass
            return f"{kode} • {nama}"

        if field_name in {"nilai_tahun_sebelumnya", "nilai_tahun_berjalan"}:
            try:
                return f"{float(text):,.0f}".replace(",", ".")
            except ValueError:
                return text
        return text
