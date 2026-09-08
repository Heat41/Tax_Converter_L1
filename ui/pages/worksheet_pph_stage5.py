from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.umkm_calculator import UMKM_MONTHS, calculate_umkm_monthly
from ui.pages.worksheet_pph_stage4 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_table_interaction, suspended_updates


class WorksheetPage(BaseWorksheetPage):
    """Stage 5 PPh: Peredaran Bruto UMKM mengikuti worksheet EVY BACHTIAR."""

    UMKM_BRUTO_COLUMN = 2
    UMKM_PPH_COLUMN = 3
    UMKM_SETOR_COLUMN = 4
    UMKM_SELISIH_COLUMN = 5
    UMKM_TOTAL_ROW = 12
    UMKM_COLUMN_WIDTHS = {
        0: 55,
        1: 130,
        2: 170,
        3: 150,
        4: 150,
        5: 150,
    }

    def __init__(self, parent=None):
        self._rendering_umkm = False
        self._umkm_bruto = [0.0] * 12
        self._umkm_pph_setor = [0.0] * 12
        self._saved_umkm_bruto = list(self._umkm_bruto)
        self._saved_umkm_pph_setor = list(self._umkm_pph_setor)
        self._last_umkm_calculation = None
        super().__init__(parent)
        self._install_pph_stage5()

    def _install_pph_stage5(self):
        layout = self.pph_tab.layout()
        if layout is None:
            return

        self.umkm_card = QFrame(objectName="card")
        card_layout = QVBoxLayout(self.umkm_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        title = QLabel("Peredaran Bruto UMKM")
        title.setObjectName("sectionTitle")
        description = QLabel(
            "Mengikuti kertas kerja EVY BACHTIAR: BRUTO dan PPh Setor diinput per masa, "
            "sedangkan PPh Final 0,5% dihitung otomatis setelah omzet kumulatif melewati Rp 500 juta."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)
        self.umkm_status = QLabel()
        self.umkm_status.setObjectName("mutedLabel")
        self.umkm_status.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(description)
        card_layout.addWidget(self.umkm_status)

        self.umkm_table = QTableWidget(13, 6)
        self.umkm_table.setHorizontalHeaderLabels(
            ["NO", "MASA", "BRUTO", "PPh", "PPh SETOR", "SELISIH"]
        )
        self.umkm_table.setAlternatingRowColors(True)
        self.umkm_table.verticalHeader().setVisible(False)
        self.umkm_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.umkm_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.umkm_table.setWordWrap(False)
        self.umkm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.umkm_table.horizontalHeader().setStretchLastSection(False)
        self.umkm_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.umkm_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.umkm_table.setMinimumHeight(485)
        optimize_table_interaction(
            self.umkm_table,
            column_widths=self.UMKM_COLUMN_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self.umkm_table.itemChanged.connect(self._on_umkm_item_changed)
        card_layout.addWidget(self.umkm_table)

        # Urutan worksheet Evy: Bupot -> UMKM -> Ringkasan/Penghasilan lainnya.
        layout.insertWidget(2, self.umkm_card)
        self.pph_tab.setMinimumHeight(max(self.pph_tab.minimumHeight(), 1450))
        self._render_umkm_table()
        self._refresh_bupot_actions()

    def _render_umkm_table(self):
        if not hasattr(self, "umkm_table"):
            return

        result = calculate_umkm_monthly(self._umkm_bruto, self._umkm_pph_setor)
        self._last_umkm_calculation = result
        self._rendering_umkm = True
        with suspended_updates(self.umkm_table):
            self.umkm_table.blockSignals(True)
            try:
                for row, month in enumerate(result.months):
                    no_item = QTableWidgetItem(str(month.nomor))
                    no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
                    self.umkm_table.setItem(row, 0, no_item)

                    masa_item = QTableWidgetItem(month.masa)
                    masa_item.setFlags(masa_item.flags() & ~Qt.ItemIsEditable)
                    self.umkm_table.setItem(row, 1, masa_item)

                    bruto_item = QTableWidgetItem(self._format_bupot_money(month.bruto))
                    bruto_item.setData(Qt.UserRole, month.bruto)
                    self.umkm_table.setItem(row, self.UMKM_BRUTO_COLUMN, bruto_item)

                    pph_item = QTableWidgetItem(self._format_bupot_money(month.pph))
                    pph_item.setData(Qt.UserRole, month.pph)
                    pph_item.setFlags(pph_item.flags() & ~Qt.ItemIsEditable)
                    self.umkm_table.setItem(row, self.UMKM_PPH_COLUMN, pph_item)

                    setor_item = QTableWidgetItem(self._format_bupot_money(month.pph_setor))
                    setor_item.setData(Qt.UserRole, month.pph_setor)
                    self.umkm_table.setItem(row, self.UMKM_SETOR_COLUMN, setor_item)

                    selisih_item = QTableWidgetItem(self._format_bupot_money(month.selisih))
                    selisih_item.setData(Qt.UserRole, month.selisih)
                    selisih_item.setFlags(selisih_item.flags() & ~Qt.ItemIsEditable)
                    self.umkm_table.setItem(row, self.UMKM_SELISIH_COLUMN, selisih_item)

                total_values = (
                    "",
                    "TOTAL",
                    result.total_bruto,
                    result.total_pph,
                    result.total_pph_setor,
                    result.total_selisih,
                )
                for column, value in enumerate(total_values):
                    text = (
                        str(value)
                        if column < 2
                        else self._format_bupot_money(value)
                    )
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    if column >= 2:
                        item.setData(Qt.UserRole, float(value))
                    self.umkm_table.setItem(self.UMKM_TOTAL_ROW, column, item)
            finally:
                self.umkm_table.blockSignals(False)
                self._rendering_umkm = False

        self.umkm_status.setText(
            f"Total Bruto Rp {self._format_bupot_money(result.total_bruto)} • "
            f"PPh Final 0,5% Rp {self._format_bupot_money(result.total_pph)} • "
            f"PPh Setor Rp {self._format_bupot_money(result.total_pph_setor)} • "
            f"Selisih Rp {self._format_bupot_money(result.total_selisih)}"
        )

    def _on_umkm_item_changed(self, item: QTableWidgetItem):
        if self._rendering_umkm or item is None:
            return
        row = item.row()
        column = item.column()
        if row < 0 or row >= 12 or column not in {
            self.UMKM_BRUTO_COLUMN,
            self.UMKM_SETOR_COLUMN,
        }:
            return

        target = self._umkm_bruto if column == self.UMKM_BRUTO_COLUMN else self._umkm_pph_setor
        previous = float(target[row])
        try:
            value = self._parse_bupot_money(item.text())
            if value < 0:
                raise ValueError("nilai negatif")
        except ValueError:
            self.umkm_table.blockSignals(True)
            try:
                item.setText(self._format_bupot_money(previous))
            finally:
                self.umkm_table.blockSignals(False)
            self.toast_notification.show_message(
                "Nilai UMKM tidak valid. Gunakan angka positif, misalnya 200.000.000.",
                "warning",
                3600,
            )
            return

        target[row] = float(value)
        self._render_umkm_table()
        self._refresh_bupot_actions()

    def _load_pph_state_for_current_wp(self):
        super()._load_pph_state_for_current_wp()
        if not hasattr(self, "umkm_table"):
            return

        npwp, year = self._current_pph_identity()
        bruto = [0.0] * 12
        setor = [0.0] * 12
        if npwp and year:
            try:
                persisted = self.pph_state_store.load(npwp, year)
            except Exception:
                persisted = None
            if persisted is not None:
                bruto = self._normalize_umkm_component(
                    persisted.components.get("umkm_bruto_bulanan")
                )
                setor = self._normalize_umkm_component(
                    persisted.components.get("umkm_pph_setor_bulanan")
                )

        self._umkm_bruto = bruto
        self._umkm_pph_setor = setor
        self._saved_umkm_bruto = list(bruto)
        self._saved_umkm_pph_setor = list(setor)
        self._render_umkm_table()
        self._refresh_bupot_actions()

    def _clear_bupot_working_state(self):
        super()._clear_bupot_working_state()
        self._umkm_bruto = [0.0] * 12
        self._umkm_pph_setor = [0.0] * 12
        self._saved_umkm_bruto = list(self._umkm_bruto)
        self._saved_umkm_pph_setor = list(self._umkm_pph_setor)
        if hasattr(self, "umkm_table"):
            self._render_umkm_table()

    @staticmethod
    def _normalize_umkm_component(value):
        if not isinstance(value, list):
            return [0.0] * 12
        result = []
        for item in value[:12]:
            try:
                result.append(max(0.0, float(item or 0)))
            except (TypeError, ValueError):
                result.append(0.0)
        result.extend([0.0] * (12 - len(result)))
        return result

    def _has_unsaved_umkm_changes(self) -> bool:
        return (
            self._umkm_bruto != self._saved_umkm_bruto
            or self._umkm_pph_setor != self._saved_umkm_pph_setor
        )

    def _has_unsaved_pph_component_changes(self) -> bool:
        return super()._has_unsaved_pph_component_changes() or self._has_unsaved_umkm_changes()

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

        self._recalculate_pph_summary()
        self._render_umkm_table()
        rows = self._snapshot_bupot_rows()
        components = {
            key: float(self._pph_component_values.get(key, 0.0))
            for key in self.COMPONENT_KEYS
        }
        components["status_ptkp"] = self._status_ptkp
        components["umkm_bruto_bulanan"] = [float(value) for value in self._umkm_bruto]
        components["umkm_pph_setor_bulanan"] = [
            float(value) for value in self._umkm_pph_setor
        ]

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
        self._saved_umkm_bruto = list(self._umkm_bruto)
        self._saved_umkm_pph_setor = list(self._umkm_pph_setor)
        self._refresh_bupot_actions()
        self.pph_validation_status.setText(
            f"✓ Worksheet PPh + UMKM tersimpan ke database untuk Tahun Pajak {year}."
        )
        self.pph_validation_status.setStyleSheet(
            "color:#1B5E20; font-weight:600;"
        )
        self.toast_notification.show_message(
            "Bupot, UMKM, dan kalkulasi PPh tersimpan ke database.", "success"
        )
        return self._bupot_last_save_result
