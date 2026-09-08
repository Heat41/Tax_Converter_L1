from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from core.pph_calculator import (
    PTKP_BY_STATUS,
    calculate_annual_pph,
    ptkp_value,
)
from ui.pages.worksheet_pph_stage3 import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Stage 4 PPh: cocokkan PPh Terutang dengan rumus sheet produksi 2025."""

    PTKP_STATUS_ORDER = (
        "TK/0", "TK/1", "TK/2", "TK/3",
        "K/0", "K/1", "K/2", "K/3",
        "K/I/0", "K/I/1", "K/I/2", "K/I/3",
    )

    def __init__(self, parent=None):
        self._status_ptkp = "TK/0"
        self._saved_status_ptkp = "TK/0"
        self._last_pph_calculation = None
        super().__init__(parent)
        self._install_pph_stage4()

    def _install_pph_stage4(self):
        if not hasattr(self, "pph_calc_grid"):
            return

        summary_card = self.pph_tab.layout().itemAt(2).widget()
        if summary_card is not None and summary_card.layout() is not None:
            note_item = summary_card.layout().itemAt(1)
            note = note_item.widget() if note_item is not None else None
            if note is not None:
                note.setText(
                    "PPh Terutang dihitung otomatis mengikuti struktur formula sheet 2025: "
                    "PTKP berdasarkan status, PKP, lalu tarif progresif 5% / 15% / 25% / 30% / 35%."
                )

        # PTKP bukan lagi input angka bebas. Tampilkan status + nilai otomatis.
        ptkp_edit = self.pph_component_edits.pop("ptkp", None)
        if ptkp_edit is not None:
            self.pph_calc_grid.removeWidget(ptkp_edit)
            ptkp_edit.setReadOnly(True)
            ptkp_edit.setObjectName("readOnlyField")
            ptkp_edit.setMaximumWidth(150)
            self.pph_auto_values["ptkp"] = ptkp_edit

            self.ptkp_status_combo = QComboBox()
            for status in self.PTKP_STATUS_ORDER:
                nilai = self._format_bupot_money(PTKP_BY_STATUS[status])
                self.ptkp_status_combo.addItem(f"{status} — Rp {nilai}", status)
            self.ptkp_status_combo.setMinimumWidth(190)
            self.ptkp_status_combo.currentIndexChanged.connect(
                self._on_ptkp_status_changed
            )

            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(8)
            holder_layout.addWidget(self.ptkp_status_combo)
            holder_layout.addWidget(ptkp_edit)
            holder_layout.addStretch()
            self.pph_calc_grid.addWidget(holder, 4, 1)

            label = self.pph_calc_grid.itemAtPosition(4, 0)
            if label is not None and label.widget() is not None:
                label.widget().setText("Status PTKP / Nilai PTKP")

        # PPh Terutang menjadi hasil kalkulasi, bukan input user.
        pph_edit = self.pph_component_edits.pop("pph_terutang", None)
        if pph_edit is not None:
            pph_edit.setReadOnly(True)
            pph_edit.setObjectName("readOnlyField")
            self.pph_auto_values["pph_terutang"] = pph_edit

        pph_label = self.pph_calc_grid.itemAtPosition(6, 0)
        if pph_label is not None and pph_label.widget() is not None:
            pph_label.widget().setText("PPh 21 Terutang")

        credit_label = self.pph_calc_grid.itemAtPosition(7, 0)
        if credit_label is not None and credit_label.widget() is not None:
            credit_label.widget().setText("PPh 21 Sudah Dipotong / Dipungut")

        pkp_label = self.pph_calc_grid.itemAtPosition(5, 0)
        if pkp_label is not None and pkp_label.widget() is not None:
            pkp_label.widget().setText("Penghasilan Kena Pajak (PKP)")

        self.pph_rounded_value = QLineEdit("0")
        self.pph_rounded_value.setReadOnly(True)
        self.pph_rounded_value.setObjectName("readOnlyField")
        self.pph_rounded_value.setAlignment(Qt.AlignRight)
        self.pph_rounded_value.setMinimumHeight(34)
        self.pph_rounded_value.setMaximumWidth(260)
        rounded_label = self._make_summary_label(
            "Kurang / (Lebih) Bayar — Pembulatan SPT"
        )
        self.pph_calc_grid.addWidget(rounded_label, 10, 0)
        self.pph_calc_grid.addWidget(self.pph_rounded_value, 10, 1)

        self.pph_tab.setMinimumHeight(max(self.pph_tab.minimumHeight(), 950))
        self._set_ptkp_combo(self._status_ptkp)
        self._recalculate_pph_summary()
        self._refresh_bupot_actions()

    @staticmethod
    def _make_summary_label(text: str):
        from PySide6.QtWidgets import QLabel
        label = QLabel(text)
        label.setObjectName("mutedLabel")
        return label

    def _set_ptkp_combo(self, status: str):
        if not hasattr(self, "ptkp_status_combo"):
            return
        index = self.ptkp_status_combo.findData(status)
        if index < 0:
            index = self.ptkp_status_combo.findData("TK/0")
        self.ptkp_status_combo.blockSignals(True)
        try:
            self.ptkp_status_combo.setCurrentIndex(index)
        finally:
            self.ptkp_status_combo.blockSignals(False)

    def _on_ptkp_status_changed(self, _index: int):
        if not hasattr(self, "ptkp_status_combo"):
            return
        status = self.ptkp_status_combo.currentData() or "TK/0"
        self._status_ptkp = str(status)
        self._recalculate_pph_summary()
        self._refresh_bupot_actions()

    def _load_pph_state_for_current_wp(self):
        super()._load_pph_state_for_current_wp()
        if not hasattr(self, "ptkp_status_combo"):
            return

        npwp, year = self._current_pph_identity()
        status = "TK/0"
        if npwp and year:
            try:
                persisted = self.pph_state_store.load(npwp, year)
            except Exception:
                persisted = None
            if persisted is not None:
                stored = str(persisted.components.get("status_ptkp") or "").strip()
                if stored in PTKP_BY_STATUS:
                    status = stored
                else:
                    # Migrasi state Stage 3 lama yang hanya menyimpan angka PTKP.
                    old_ptkp = float(persisted.components.get("ptkp", 0) or 0)
                    status = self._best_status_for_old_ptkp(old_ptkp)

        self._status_ptkp = status
        self._saved_status_ptkp = status
        self._set_ptkp_combo(status)
        self._recalculate_pph_summary()
        self._pph_saved_components["ptkp"] = float(
            self._pph_component_values.get("ptkp", ptkp_value(status))
        )
        self._pph_saved_components["pph_terutang"] = float(
            self._pph_component_values.get("pph_terutang", 0.0)
        )
        self._refresh_bupot_actions()

    @classmethod
    def _best_status_for_old_ptkp(cls, value: float) -> str:
        if not value:
            return "TK/0"
        for status in cls.PTKP_STATUS_ORDER:
            if abs(PTKP_BY_STATUS[status] - float(value)) < 0.5:
                return status
        return "TK/0"

    def _clear_bupot_working_state(self):
        super()._clear_bupot_working_state()
        self._status_ptkp = "TK/0"
        self._saved_status_ptkp = "TK/0"
        if hasattr(self, "ptkp_status_combo"):
            self._set_ptkp_combo("TK/0")
            self._recalculate_pph_summary()

    def _recalculate_pph_summary(self):
        # Saat BaseWorksheetPage masih membangun UI, gunakan kalkulasi Stage 3 dulu.
        if not hasattr(self, "pph_auto_values"):
            return
        if not hasattr(self, "ptkp_status_combo"):
            return BaseWorksheetPage._recalculate_pph_summary(self)

        total_netto = sum(
            self._money_value(row, self.BUPOT_NETTO_COLUMN)
            for row in range(self.bupot_table.rowCount())
        )
        lainnya = float(
            self._pph_component_values.get("penghasilan_neto_lainnya", 0.0)
        )
        pengurang = float(
            self._pph_component_values.get("pengurang_penghasilan_neto", 0.0)
        )
        kredit = float(self._pph_component_values.get("kredit_pajak", 0.0))
        pph25 = float(self._pph_component_values.get("pph25", 0.0))

        result = calculate_annual_pph(
            total_netto_bupot=total_netto,
            penghasilan_neto_lainnya=lainnya,
            pengurang_penghasilan_neto=pengurang,
            status_ptkp=self._status_ptkp,
            kredit_pajak=kredit,
            pph25=pph25,
        )
        self._last_pph_calculation = result
        self._pph_component_values["ptkp"] = result.ptkp
        self._pph_component_values["pph_terutang"] = result.pph_terutang

        values = {
            "total_netto_bupot": result.total_netto_bupot,
            "penghasilan_neto_gabungan": result.penghasilan_neto_gabungan,
            "ptkp": result.ptkp,
            "pkp_simulasi": result.pkp,
            "pph_terutang": result.pph_terutang,
            "kurang_lebih_bayar": result.kurang_lebih_bayar,
        }
        for key, value in values.items():
            edit = self.pph_auto_values.get(key)
            if edit is not None:
                edit.setText(self._format_bupot_money(value))

        if hasattr(self, "pph_rounded_value"):
            self.pph_rounded_value.setText(
                self._format_bupot_money(result.kurang_lebih_bayar_pembulatan)
            )

    def _has_unsaved_pph_component_changes(self) -> bool:
        return (
            super()._has_unsaved_pph_component_changes()
            or self._status_ptkp != self._saved_status_ptkp
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
                "Worksheet PPh belum dapat disimpan karena Bupot masih tidak valid.",
                "warning",
                3600,
            )
            return None

        self._recalculate_pph_summary()
        rows = self._snapshot_bupot_rows()
        components = {
            key: float(self._pph_component_values.get(key, 0.0))
            for key in self.COMPONENT_KEYS
        }
        components["status_ptkp"] = self._status_ptkp

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
        self._pph_saved_components = {
            key: float(self._pph_component_values.get(key, 0.0))
            for key in self.COMPONENT_KEYS
        }
        self._saved_status_ptkp = self._status_ptkp
        self._refresh_bupot_actions()
        self.pph_validation_status.setText(
            f"✓ Worksheet PPh tersimpan ke database untuk Tahun Pajak {year}."
        )
        self.pph_validation_status.setStyleSheet(
            "color:#1B5E20; font-weight:600;"
        )
        self.toast_notification.show_message(
            "Bupot dan kalkulasi PPh otomatis tersimpan ke database.", "success"
        )
        return self._bupot_last_save_result
