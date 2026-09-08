from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from ui.pages.worksheet_pph_windowed import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Stage 3 Penghasilan & PPh: ringkasan perhitungan tahunan dasar.

    Tahap ini hanya memakai aritmetika worksheet yang sudah jelas. PPh Terutang
    tetap diinput manual sampai tarif/aturan produksi pada worksheet kantor
    dikunci pada tahap berikutnya.
    """

    COMPONENT_KEYS = (
        "penghasilan_neto_lainnya",
        "pengurang_penghasilan_neto",
        "ptkp",
        "pph_terutang",
        "kredit_pajak",
        "pph25",
    )

    def __init__(self, parent=None):
        self._pph_component_values = {key: 0.0 for key in self.COMPONENT_KEYS}
        self._pph_saved_components = dict(self._pph_component_values)
        self._rendering_pph_components = False
        super().__init__(parent)
        self._install_pph_stage3()

    def _install_pph_stage3(self):
        summary_card = self.pph_tab.layout().itemAt(2).widget()
        if summary_card is None or summary_card.layout() is None:
            return

        summary_layout = summary_card.layout()
        note_item = summary_layout.itemAt(1)
        note = note_item.widget() if note_item is not None else None
        if isinstance(note, QLabel):
            note.setText(
                "Ringkasan tahap awal menghubungkan NETTO Bupot dengan komponen manual. "
                "PPh Terutang masih diinput manual sampai formula produksi dikunci."
            )

        self.pph_calc_grid = QGridLayout()
        self.pph_calc_grid.setContentsMargins(0, 10, 0, 4)
        self.pph_calc_grid.setHorizontalSpacing(18)
        self.pph_calc_grid.setVerticalSpacing(9)

        rows = (
            ("Total Netto Bupot", "total_netto_bupot", False),
            ("Penghasilan Neto Lainnya", "penghasilan_neto_lainnya", True),
            ("Pengurang Penghasilan Neto", "pengurang_penghasilan_neto", True),
            ("Penghasilan Neto Gabungan", "penghasilan_neto_gabungan", False),
            ("PTKP", "ptkp", True),
            ("PKP Simulasi", "pkp_simulasi", False),
            ("PPh Terutang", "pph_terutang", True),
            ("Kredit Pajak", "kredit_pajak", True),
            ("Angsuran PPh 25", "pph25", True),
            ("Kurang / (Lebih) Bayar", "kurang_lebih_bayar", False),
        )

        self.pph_component_edits = {}
        self.pph_auto_values = {}
        for row_index, (caption, key, editable) in enumerate(rows):
            label = QLabel(caption)
            label.setObjectName("mutedLabel")
            self.pph_calc_grid.addWidget(label, row_index, 0)

            edit = QLineEdit("0")
            edit.setAlignment(Qt.AlignRight)
            edit.setMinimumHeight(34)
            edit.setMaximumWidth(260)
            if editable:
                edit.setPlaceholderText("0")
                edit.editingFinished.connect(
                    lambda component_key=key: self._on_pph_component_finished(component_key)
                )
                self.pph_component_edits[key] = edit
            else:
                edit.setReadOnly(True)
                edit.setObjectName("readOnlyField")
                self.pph_auto_values[key] = edit
            self.pph_calc_grid.addWidget(edit, row_index, 1)

        self.pph_calc_grid.setColumnStretch(0, 1)
        summary_layout.addLayout(self.pph_calc_grid)

        self.save_pph_summary_button = QPushButton("Simpan Ringkasan PPh")
        self.save_pph_summary_button.setObjectName("primaryButton")
        self.save_pph_summary_button.setMinimumWidth(180)
        self.save_pph_summary_button.clicked.connect(self.save_bupot_changes)
        summary_layout.addWidget(self.save_pph_summary_button, alignment=Qt.AlignLeft)

        # Konten bertambah; pastikan mode windowed punya range scroll vertikal.
        self.pph_tab.setMinimumHeight(max(self.pph_tab.minimumHeight(), 900))
        self._render_pph_components()
        self._recalculate_pph_summary()
        self._refresh_bupot_actions()

    def _load_pph_state_for_current_wp(self):
        super()._load_pph_state_for_current_wp()
        if not hasattr(self, "pph_component_edits"):
            return

        npwp, year = self._current_pph_identity()
        loaded = {key: 0.0 for key in self.COMPONENT_KEYS}
        if npwp and year:
            try:
                persisted = self.pph_state_store.load(npwp, year)
            except Exception:
                persisted = None
            if persisted is not None:
                for key in self.COMPONENT_KEYS:
                    try:
                        loaded[key] = float(persisted.components.get(key, 0) or 0)
                    except (TypeError, ValueError):
                        loaded[key] = 0.0

        self._pph_component_values = loaded
        self._pph_saved_components = dict(loaded)
        self._render_pph_components()
        self._recalculate_pph_summary()
        self._refresh_bupot_actions()

    def _clear_bupot_working_state(self):
        super()._clear_bupot_working_state()
        self._pph_component_values = {key: 0.0 for key in self.COMPONENT_KEYS}
        self._pph_saved_components = dict(self._pph_component_values)
        if hasattr(self, "pph_component_edits"):
            self._render_pph_components()
            self._recalculate_pph_summary()

    def _refresh_pph_status(self):
        super()._refresh_pph_status()
        if hasattr(self, "pph_auto_values"):
            self._recalculate_pph_summary()

    def _on_pph_component_finished(self, key: str):
        if self._rendering_pph_components:
            return
        edit = self.pph_component_edits.get(key)
        if edit is None:
            return

        previous = float(self._pph_component_values.get(key, 0.0))
        try:
            value = self._parse_bupot_money(edit.text())
        except ValueError:
            value = previous
            self.toast_notification.show_message(
                "Nilai ringkasan PPh tidak valid. Gunakan angka, misalnya 54.000.000.",
                "warning",
                3600,
            )

        self._pph_component_values[key] = float(value)
        self._rendering_pph_components = True
        try:
            edit.setText(self._format_bupot_money(value))
        finally:
            self._rendering_pph_components = False

        self._recalculate_pph_summary()
        self._refresh_bupot_actions()

    def _render_pph_components(self):
        if not hasattr(self, "pph_component_edits"):
            return
        self._rendering_pph_components = True
        try:
            for key, edit in self.pph_component_edits.items():
                edit.setText(
                    self._format_bupot_money(self._pph_component_values.get(key, 0.0))
                )
        finally:
            self._rendering_pph_components = False

    def _recalculate_pph_summary(self):
        if not hasattr(self, "pph_auto_values"):
            return

        total_netto = sum(
            self._money_value(row, self.BUPOT_NETTO_COLUMN)
            for row in range(self.bupot_table.rowCount())
        )
        lainnya = float(self._pph_component_values.get("penghasilan_neto_lainnya", 0.0))
        pengurang = float(self._pph_component_values.get("pengurang_penghasilan_neto", 0.0))
        ptkp = float(self._pph_component_values.get("ptkp", 0.0))
        pph_terutang = float(self._pph_component_values.get("pph_terutang", 0.0))
        kredit = float(self._pph_component_values.get("kredit_pajak", 0.0))
        pph25 = float(self._pph_component_values.get("pph25", 0.0))

        neto_gabungan = total_netto + lainnya - pengurang
        pkp = max(0.0, neto_gabungan - ptkp)
        kurang_lebih = pph_terutang - kredit - pph25

        values = {
            "total_netto_bupot": total_netto,
            "penghasilan_neto_gabungan": neto_gabungan,
            "pkp_simulasi": pkp,
            "kurang_lebih_bayar": kurang_lebih,
        }
        for key, value in values.items():
            edit = self.pph_auto_values.get(key)
            if edit is not None:
                edit.setText(self._format_bupot_money(value))

    def _has_unsaved_pph_component_changes(self) -> bool:
        return self._pph_component_values != self._pph_saved_components

    def _refresh_bupot_actions(self):
        super()._refresh_bupot_actions()
        if not hasattr(self, "save_bupot_button"):
            return

        npwp, year = self._current_pph_identity()
        errors = self._validate_bupot_rows()
        has_unsaved = (
            self._has_unsaved_bupot_changes()
            or self._has_unsaved_pph_component_changes()
        )
        enabled = bool(npwp and year) and not errors and has_unsaved
        self.save_bupot_button.setEnabled(enabled)
        if hasattr(self, "save_pph_summary_button"):
            self.save_pph_summary_button.setEnabled(enabled)

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
                "Worksheet PPh belum dapat disimpan karena Bupot masih tidak valid.",
                "warning",
                3600,
            )
            return None

        rows = self._snapshot_bupot_rows()
        components = {
            key: float(self._pph_component_values.get(key, 0.0))
            for key in self.COMPONENT_KEYS
        }
        self._bupot_last_save_error = None
        self._bupot_last_save_result = None
        try:
            self._bupot_last_save_result = self.pph_state_store.save(
                npwp=npwp,
                tahun_pajak=year,
                bupot_rows=rows,
                components=components,
            )
        except Exception as exc:
            self._bupot_last_save_error = str(exc)
            self.toast_notification.show_message(
                "Worksheet PPh gagal disimpan ke database.", "error", 3600
            )
            return None

        self._bupot_saved_rows = list(rows)
        self._pph_saved_components = dict(components)
        self._refresh_bupot_actions()
        self.pph_validation_status.setText(
            f"✓ Worksheet PPh tersimpan ke database untuk Tahun Pajak {year}."
        )
        self.pph_validation_status.setStyleSheet("color:#1B5E20; font-weight:600;")
        self.toast_notification.show_message(
            "Bupot dan Ringkasan PPh tersimpan ke database.", "success"
        )
        return self._bupot_last_save_result
