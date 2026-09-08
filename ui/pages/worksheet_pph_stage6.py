from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.evy_other_income import (
    FinalOtherIncomeRow,
    calculate_final_other_income,
    default_evy_final_other_income_rows,
)
from ui.pages.worksheet_pph_stage5 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_table_interaction, suspended_updates


class WorksheetPage(BaseWorksheetPage):
    """Stage 6 PPh: Penghasilan Lainnya dan Pengurang Neto acuan EVY BACHTIAR."""

    GENERAL_ROWS = (
        ("domestic_other", "Penghasilan Dalam Negeri Lainnya"),
        ("sewa", "Sewa atas Tanah dan/atau Bangunan"),
        ("honor", "Honor"),
        ("pekerjaan_bebas", "Pekerjaan Bebas"),
        ("prive", "Prive"),
        ("hibah_warisan", "Hibah / Warisan"),
    )
    GENERAL_DPP_COLUMN = 2
    GENERAL_PPH_COLUMN = 3

    def __init__(self, parent=None):
        self._rendering_other_income = False
        self._other_income_state = self._default_other_income_state()
        self._saved_other_income_state = deepcopy(self._other_income_state)
        self._final_other_income_rows = default_evy_final_other_income_rows()
        self._saved_final_other_income_rows = list(self._final_other_income_rows)
        self._last_final_other_income = None
        super().__init__(parent)
        self._install_pph_stage6()

    @staticmethod
    def _default_other_income_state():
        return {
            "domestic_other_enabled": False,
            "domestic_other_dpp": 0.0,
            "sewa_dpp": 0.0,
            "sewa_pph": 0.0,
            "honor_dpp": 0.0,
            "honor_pph": 0.0,
            "pekerjaan_bebas_dpp": 0.0,
            "prive_dpp": 0.0,
            "hibah_warisan_dpp": 0.0,
            "hibah_warisan_note": "",
            "zakat": 0.0,
        }

    def _install_pph_stage6(self):
        layout = self.pph_tab.layout()
        if layout is None:
            return

        self._lock_summary_component("penghasilan_neto_lainnya", 1)
        self._lock_summary_component("pengurang_penghasilan_neto", 2)

        self.other_income_card = QFrame(objectName="card")
        card_layout = QVBoxLayout(self.other_income_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        title = QLabel("Penghasilan Lainnya & Pengurang Penghasilan Neto")
        title.setObjectName("sectionTitle")
        description = QLabel(
            "Mengikuti kertas kerja EVY BACHTIAR. Penghasilan Dalam Negeri Lainnya "
            "masuk ke penghasilan neto progresif, sedangkan pos lain dicatat terpisah. "
            "Zakat menjadi pengurang penghasilan neto."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)
        self.other_income_status = QLabel()
        self.other_income_status.setObjectName("mutedLabel")
        self.other_income_status.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(description)
        card_layout.addWidget(self.other_income_status)

        self.other_income_table = QTableWidget(len(self.GENERAL_ROWS), 4)
        self.other_income_table.setHorizontalHeaderLabels(
            ["JENIS", "STATUS / KETERANGAN", "DPP", "PPh"]
        )
        self.other_income_table.verticalHeader().setVisible(False)
        self.other_income_table.setAlternatingRowColors(True)
        self.other_income_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.other_income_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.other_income_table.setWordWrap(False)
        self.other_income_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.other_income_table.setMinimumHeight(245)
        optimize_table_interaction(
            self.other_income_table,
            column_widths={0: 285, 1: 210, 2: 160, 3: 160},
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self.other_income_table.itemChanged.connect(self._on_other_income_item_changed)
        card_layout.addWidget(self.other_income_table)

        self.domestic_other_combo = QComboBox()
        self.domestic_other_combo.addItem("TIDAK", False)
        self.domestic_other_combo.addItem("ADA", True)
        self.domestic_other_combo.currentIndexChanged.connect(
            self._on_domestic_other_status_changed
        )
        self.other_income_table.setCellWidget(0, 1, self.domestic_other_combo)

        final_header = QHBoxLayout()
        final_title = QLabel("Penghasilan Final Lainnya — Detail")
        final_title.setObjectName("sectionTitle")
        self.add_final_income_button = QPushButton("+ Tambah Detail")
        self.add_final_income_button.setObjectName("secondaryButton")
        self.remove_final_income_button = QPushButton("Hapus Detail")
        self.remove_final_income_button.setObjectName("secondaryButton")
        self.add_final_income_button.clicked.connect(self._add_final_income_row)
        self.remove_final_income_button.clicked.connect(self._remove_final_income_row)
        final_header.addWidget(final_title)
        final_header.addStretch()
        final_header.addWidget(self.add_final_income_button)
        final_header.addWidget(self.remove_final_income_button)
        card_layout.addLayout(final_header)

        self.final_income_table = QTableWidget(0, 4)
        self.final_income_table.setHorizontalHeaderLabels(
            ["KETERANGAN", "DPP", "TARIF", "PPh"]
        )
        self.final_income_table.verticalHeader().setVisible(False)
        self.final_income_table.setAlternatingRowColors(True)
        self.final_income_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.final_income_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.final_income_table.setWordWrap(False)
        self.final_income_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.final_income_table.setMinimumHeight(165)
        optimize_table_interaction(
            self.final_income_table,
            column_widths={0: 280, 1: 175, 2: 120, 3: 175},
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self.final_income_table.itemChanged.connect(self._on_final_income_item_changed)
        card_layout.addWidget(self.final_income_table)

        self.final_income_status = QLabel()
        self.final_income_status.setObjectName("mutedLabel")
        card_layout.addWidget(self.final_income_status)

        zakat_row = QHBoxLayout()
        zakat_label = QLabel("Zakat / Pengurang Penghasilan Neto")
        zakat_label.setObjectName("mutedLabel")
        self.zakat_edit = QLineEdit("0")
        self.zakat_edit.setAlignment(Qt.AlignRight)
        self.zakat_edit.setMaximumWidth(260)
        self.zakat_edit.setMinimumHeight(34)
        self.zakat_edit.editingFinished.connect(self._on_zakat_finished)
        zakat_row.addWidget(zakat_label)
        zakat_row.addStretch()
        zakat_row.addWidget(self.zakat_edit)
        card_layout.addLayout(zakat_row)

        # Bupot -> UMKM -> Penghasilan Lainnya -> Ringkasan.
        layout.insertWidget(3, self.other_income_card)
        self.pph_tab.setMinimumHeight(max(self.pph_tab.minimumHeight(), 2050))
        self._render_other_income()
        self._sync_other_income_to_summary()
        self._refresh_bupot_actions()

    def _lock_summary_component(self, key: str, row_index: int):
        edit = getattr(self, "pph_component_edits", {}).pop(key, None)
        if edit is not None:
            edit.setReadOnly(True)
            edit.setObjectName("readOnlyField")
            self.pph_auto_values[key] = edit
        label_item = self.pph_calc_grid.itemAtPosition(row_index, 0)
        if label_item is not None and label_item.widget() is not None:
            if key == "penghasilan_neto_lainnya":
                label_item.widget().setText("Penghasilan Dalam Negeri Lainnya")
            else:
                label_item.widget().setText("Zakat / Pengurang Penghasilan Neto")

    def _render_other_income(self):
        if not hasattr(self, "other_income_table"):
            return

        self._rendering_other_income = True
        with suspended_updates(self.other_income_table):
            self.other_income_table.blockSignals(True)
            try:
                for row, (key, caption) in enumerate(self.GENERAL_ROWS):
                    name_item = QTableWidgetItem(caption)
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    self.other_income_table.setItem(row, 0, name_item)

                    if row != 0:
                        note = (
                            self._other_income_state.get("hibah_warisan_note", "")
                            if key == "hibah_warisan"
                            else ""
                        )
                        note_item = QTableWidgetItem(str(note or ""))
                        if key != "hibah_warisan":
                            note_item.setFlags(note_item.flags() & ~Qt.ItemIsEditable)
                        self.other_income_table.setItem(row, 1, note_item)

                    dpp_key = (
                        "domestic_other_dpp"
                        if key == "domestic_other"
                        else f"{key}_dpp"
                    )
                    dpp_value = float(self._other_income_state.get(dpp_key, 0.0) or 0)
                    if key == "domestic_other" and not self._other_income_state["domestic_other_enabled"]:
                        dpp_value = 0.0
                    dpp_item = QTableWidgetItem(self._format_bupot_money(dpp_value))
                    dpp_item.setData(Qt.UserRole, dpp_value)
                    if key == "domestic_other" and not self._other_income_state["domestic_other_enabled"]:
                        dpp_item.setFlags(dpp_item.flags() & ~Qt.ItemIsEditable)
                    self.other_income_table.setItem(row, self.GENERAL_DPP_COLUMN, dpp_item)

                    pph_key = f"{key}_pph"
                    pph_value = float(self._other_income_state.get(pph_key, 0.0) or 0)
                    pph_item = QTableWidgetItem(self._format_bupot_money(pph_value))
                    pph_item.setData(Qt.UserRole, pph_value)
                    if key not in {"sewa", "honor"}:
                        pph_item.setFlags(pph_item.flags() & ~Qt.ItemIsEditable)
                    self.other_income_table.setItem(row, self.GENERAL_PPH_COLUMN, pph_item)
            finally:
                self.other_income_table.blockSignals(False)

        self.domestic_other_combo.blockSignals(True)
        try:
            self.domestic_other_combo.setCurrentIndex(
                1 if self._other_income_state["domestic_other_enabled"] else 0
            )
        finally:
            self.domestic_other_combo.blockSignals(False)

        self._render_final_income_table()
        self.zakat_edit.blockSignals(True)
        try:
            self.zakat_edit.setText(
                self._format_bupot_money(self._other_income_state.get("zakat", 0.0))
            )
        finally:
            self.zakat_edit.blockSignals(False)
        self._rendering_other_income = False
        self._refresh_other_income_status()

    def _render_final_income_table(self):
        result = calculate_final_other_income(self._final_other_income_rows)
        self._last_final_other_income = result
        with suspended_updates(self.final_income_table):
            self.final_income_table.blockSignals(True)
            try:
                self.final_income_table.clearContents()
                self.final_income_table.setRowCount(len(result.rows))
                for row, item_data in enumerate(result.rows):
                    desc = QTableWidgetItem(item_data.keterangan)
                    dpp = QTableWidgetItem(self._format_bupot_money(item_data.dpp))
                    dpp.setData(Qt.UserRole, item_data.dpp)
                    rate = QTableWidgetItem(self._format_rate(item_data.tarif))
                    rate.setData(Qt.UserRole, item_data.tarif)
                    pph = QTableWidgetItem(self._format_bupot_money(item_data.pph))
                    pph.setData(Qt.UserRole, item_data.pph)
                    pph.setFlags(pph.flags() & ~Qt.ItemIsEditable)
                    self.final_income_table.setItem(row, 0, desc)
                    self.final_income_table.setItem(row, 1, dpp)
                    self.final_income_table.setItem(row, 2, rate)
                    self.final_income_table.setItem(row, 3, pph)
            finally:
                self.final_income_table.blockSignals(False)

        self.remove_final_income_button.setEnabled(bool(result.rows))
        self.final_income_status.setText(
            f"Subtotal Penghasilan Final Lainnya • DPP Rp {self._format_bupot_money(result.total_dpp)} • "
            f"PPh Rp {self._format_bupot_money(result.total_pph)}"
        )

    def _refresh_other_income_status(self):
        domestic = (
            float(self._other_income_state.get("domestic_other_dpp", 0.0))
            if self._other_income_state.get("domestic_other_enabled")
            else 0.0
        )
        zakat = float(self._other_income_state.get("zakat", 0.0))
        self.other_income_status.setText(
            f"Penghasilan Dalam Negeri Lainnya Rp {self._format_bupot_money(domestic)} • "
            f"Zakat/Pengurang Neto Rp {self._format_bupot_money(zakat)}"
        )

    def _on_domestic_other_status_changed(self, _index: int):
        if self._rendering_other_income:
            return
        enabled = bool(self.domestic_other_combo.currentData())
        self._other_income_state["domestic_other_enabled"] = enabled
        if not enabled:
            self._other_income_state["domestic_other_dpp"] = 0.0
        self._render_other_income()
        self._sync_other_income_to_summary()
        self._refresh_bupot_actions()

    def _on_other_income_item_changed(self, item: QTableWidgetItem):
        if self._rendering_other_income or item is None:
            return
        row = item.row()
        column = item.column()
        if row < 0 or row >= len(self.GENERAL_ROWS):
            return
        key = self.GENERAL_ROWS[row][0]

        if column == 1 and key == "hibah_warisan":
            self._other_income_state["hibah_warisan_note"] = " ".join(
                str(item.text() or "").strip().split()
            )
        elif column in {self.GENERAL_DPP_COLUMN, self.GENERAL_PPH_COLUMN}:
            if column == self.GENERAL_PPH_COLUMN and key not in {"sewa", "honor"}:
                return
            if column == self.GENERAL_DPP_COLUMN and key == "domestic_other" and not self._other_income_state["domestic_other_enabled"]:
                return
            previous_key = (
                "domestic_other_dpp"
                if key == "domestic_other" and column == self.GENERAL_DPP_COLUMN
                else f"{key}_{'dpp' if column == self.GENERAL_DPP_COLUMN else 'pph'}"
            )
            previous = float(self._other_income_state.get(previous_key, 0.0) or 0)
            try:
                value = self._parse_bupot_money(item.text())
                if value < 0:
                    raise ValueError("negative")
            except ValueError:
                value = previous
                self.toast_notification.show_message(
                    "Nilai Penghasilan Lainnya tidak valid. Gunakan angka positif.",
                    "warning",
                    3600,
                )
            self._other_income_state[previous_key] = float(value)

        self._render_other_income()
        self._sync_other_income_to_summary()
        self._refresh_bupot_actions()

    def _on_final_income_item_changed(self, item: QTableWidgetItem):
        if self._rendering_other_income or item is None:
            return
        row = item.row()
        if row < 0 or row >= len(self._final_other_income_rows):
            return
        old = self._final_other_income_rows[row]
        try:
            if item.column() == 0:
                new = FinalOtherIncomeRow(
                    " ".join(str(item.text() or "").strip().split()), old.dpp, old.tarif
                )
            elif item.column() == 1:
                dpp = self._parse_bupot_money(item.text())
                if dpp < 0:
                    raise ValueError("negative")
                new = FinalOtherIncomeRow(old.keterangan, dpp, old.tarif)
            elif item.column() == 2:
                rate = self._parse_rate(item.text())
                new = FinalOtherIncomeRow(old.keterangan, old.dpp, rate)
            else:
                return
        except ValueError:
            self.toast_notification.show_message(
                "Detail penghasilan final tidak valid. DPP harus positif dan tarif dapat ditulis 20% atau 20.",
                "warning",
                3600,
            )
            new = old

        self._final_other_income_rows[row] = new
        self._render_final_income_table()
        self._refresh_bupot_actions()

    def _add_final_income_row(self):
        self._final_other_income_rows.append(
            FinalOtherIncomeRow("Final Lainnya", 0.0, 0.0)
        )
        self._render_final_income_table()
        if self.final_income_table.rowCount():
            self.final_income_table.selectRow(self.final_income_table.rowCount() - 1)
        self._refresh_bupot_actions()

    def _remove_final_income_row(self):
        row = self.final_income_table.currentRow()
        if row < 0 and self._final_other_income_rows:
            row = len(self._final_other_income_rows) - 1
        if 0 <= row < len(self._final_other_income_rows):
            del self._final_other_income_rows[row]
            self._render_final_income_table()
            self._refresh_bupot_actions()

    def _on_zakat_finished(self):
        if self._rendering_other_income:
            return
        previous = float(self._other_income_state.get("zakat", 0.0) or 0)
        try:
            value = self._parse_bupot_money(self.zakat_edit.text())
            if value < 0:
                raise ValueError("negative")
        except ValueError:
            value = previous
            self.toast_notification.show_message(
                "Nilai Zakat tidak valid. Gunakan angka positif.", "warning", 3600
            )
        self._other_income_state["zakat"] = float(value)
        self._render_other_income()
        self._sync_other_income_to_summary()
        self._refresh_bupot_actions()

    def _sync_other_income_to_summary(self):
        domestic = (
            float(self._other_income_state.get("domestic_other_dpp", 0.0))
            if self._other_income_state.get("domestic_other_enabled")
            else 0.0
        )
        zakat = float(self._other_income_state.get("zakat", 0.0))
        self._pph_component_values["penghasilan_neto_lainnya"] = domestic
        self._pph_component_values["pengurang_penghasilan_neto"] = zakat
        self._recalculate_pph_summary()

    def _load_pph_state_for_current_wp(self):
        super()._load_pph_state_for_current_wp()
        if not hasattr(self, "other_income_table"):
            return

        state = self._default_other_income_state()
        final_rows = default_evy_final_other_income_rows()
        npwp, year = self._current_pph_identity()
        if npwp and year:
            try:
                persisted = self.pph_state_store.load(npwp, year)
            except Exception:
                persisted = None
            if persisted is not None:
                raw_state = persisted.components.get("evy_other_income")
                if isinstance(raw_state, dict):
                    for key in state:
                        if key in raw_state:
                            if key in {"domestic_other_enabled"}:
                                state[key] = bool(raw_state[key])
                            elif key.endswith("_note"):
                                state[key] = str(raw_state[key] or "")
                            else:
                                try:
                                    state[key] = max(0.0, float(raw_state[key] or 0))
                                except (TypeError, ValueError):
                                    pass
                raw_final = persisted.components.get("evy_final_other_income_rows")
                if isinstance(raw_final, list):
                    parsed = []
                    for item in raw_final:
                        if not isinstance(item, dict):
                            continue
                        try:
                            parsed.append(
                                FinalOtherIncomeRow(
                                    str(item.get("keterangan") or ""),
                                    max(0.0, float(item.get("dpp") or 0)),
                                    max(0.0, float(item.get("tarif") or 0)),
                                )
                            )
                        except (TypeError, ValueError):
                            continue
                    final_rows = parsed

        self._other_income_state = state
        self._saved_other_income_state = deepcopy(state)
        self._final_other_income_rows = list(final_rows)
        self._saved_final_other_income_rows = list(final_rows)
        self._render_other_income()
        self._sync_other_income_to_summary()
        self._refresh_bupot_actions()

    def _clear_bupot_working_state(self):
        super()._clear_bupot_working_state()
        self._other_income_state = self._default_other_income_state()
        self._saved_other_income_state = deepcopy(self._other_income_state)
        self._final_other_income_rows = default_evy_final_other_income_rows()
        self._saved_final_other_income_rows = list(self._final_other_income_rows)
        if hasattr(self, "other_income_table"):
            self._render_other_income()
            self._sync_other_income_to_summary()

    def _has_unsaved_other_income_changes(self) -> bool:
        return (
            self._other_income_state != self._saved_other_income_state
            or self._final_other_income_rows != self._saved_final_other_income_rows
        )

    def _has_unsaved_pph_component_changes(self) -> bool:
        return (
            super()._has_unsaved_pph_component_changes()
            or self._has_unsaved_other_income_changes()
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

        self._sync_other_income_to_summary()
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
        components["evy_other_income"] = deepcopy(self._other_income_state)
        components["evy_final_other_income_rows"] = [
            {
                "keterangan": row.keterangan,
                "dpp": float(row.dpp),
                "tarif": float(row.tarif),
            }
            for row in self._final_other_income_rows
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
        self._saved_other_income_state = deepcopy(self._other_income_state)
        self._saved_final_other_income_rows = list(self._final_other_income_rows)
        self._refresh_bupot_actions()
        self.pph_validation_status.setText(
            f"✓ Worksheet PPh lengkap tersimpan ke database untuk Tahun Pajak {year}."
        )
        self.pph_validation_status.setStyleSheet(
            "color:#1B5E20; font-weight:600;"
        )
        self.toast_notification.show_message(
            "Bupot, UMKM, Penghasilan Lainnya, dan kalkulasi PPh tersimpan ke database.",
            "success",
        )
        return self._bupot_last_save_result

    @staticmethod
    def _parse_rate(value: object) -> float:
        text = str(value or "").strip().replace(" ", "")
        if not text:
            return 0.0
        percent = text.endswith("%")
        if percent:
            text = text[:-1]
        text = text.replace(",", ".")
        try:
            number = float(text)
        except ValueError as exc:
            raise ValueError("tarif tidak valid") from exc
        if number < 0:
            raise ValueError("tarif negatif")
        if percent or number > 1:
            number /= 100.0
        return number

    @staticmethod
    def _format_rate(value: object) -> str:
        try:
            rate = float(value or 0)
        except (TypeError, ValueError):
            rate = 0.0
        percent = rate * 100
        if abs(percent - round(percent)) < 1e-9:
            return f"{int(round(percent))}%"
        return f"{percent:.2f}%".replace(".", ",")
