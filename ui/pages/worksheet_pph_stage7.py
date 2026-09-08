from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.evy_other_income import calculate_final_other_income
from core.evy_reconciliation import calculate_evy_reconciliation
from ui.pages.worksheet_pph_stage6 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_scroll_area, optimize_table_interaction, suspended_updates


class WorksheetPage(BaseWorksheetPage):
    """Stage 7: Analisis Penghasilan vs Kenaikan Harta acuan EVY BACHTIAR."""

    ANALYSIS_MANUAL_ROW_KEYS = {
        3: "pengeluaran_lain_lain",
        4: "kerugian_keuntungan_penjualan_aset",
        5: "utang_baru_atas_kredit",
        6: "harta_baru_dari_kredit",
    }

    def __init__(self, parent=None):
        self._rendering_reconciliation = False
        self._reconciliation_manual = self._default_reconciliation_manual()
        self._saved_reconciliation_manual = deepcopy(self._reconciliation_manual)
        self._last_reconciliation = None
        super().__init__(parent)
        self._install_pph_stage7()

    @staticmethod
    def _default_reconciliation_manual():
        return {
            "utang_sebelumnya": 0.0,
            "utang_berjalan": 0.0,
            "pengeluaran_lain_lain": 0.0,
            "kerugian_keuntungan_penjualan_aset": 0.0,
            "utang_baru_atas_kredit": 0.0,
            "harta_baru_dari_kredit": 0.0,
            "penambahan_penghasilan_bruto_umkm": 0.0,
            "margin_usaha": 0.0,
        }

    def _install_pph_stage7(self):
        content = QWidget()
        content.setMinimumWidth(0)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 20, 18, 18)
        content_layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)
        title = QLabel("Perhitungan Penghasilan vs Kenaikan Harta")
        title.setObjectName("sectionTitle")
        description = QLabel(
            "Mengikuti blok ANALISIS pada SIMULASI I kertas kerja EVY BACHTIAR. "
            "Total Harta diambil otomatis dari Edited / Current. Total Utang sementara "
            "diinput manual sampai modul L-2 Utang disambungkan."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)
        self.reconciliation_status = QLabel("Belum ada data yang direkonsiliasi.")
        self.reconciliation_status.setObjectName("mutedLabel")
        self.reconciliation_status.setWordWrap(True)
        info_layout.addWidget(title)
        info_layout.addWidget(description)
        info_layout.addWidget(self.reconciliation_status)
        content_layout.addWidget(info_card)

        source_card = QFrame(objectName="card")
        source_layout = QGridLayout(source_card)
        source_layout.setContentsMargins(20, 16, 20, 16)
        source_layout.setHorizontalSpacing(16)
        source_layout.setVerticalSpacing(8)

        self.harta_prev_value = self._read_only_field()
        self.harta_now_value = self._read_only_field()
        self.utang_prev_edit = self._money_edit()
        self.utang_now_edit = self._money_edit()
        self.utang_prev_edit.editingFinished.connect(
            lambda: self._on_reconciliation_field_finished("utang_sebelumnya")
        )
        self.utang_now_edit.editingFinished.connect(
            lambda: self._on_reconciliation_field_finished("utang_berjalan")
        )

        source_layout.addWidget(QLabel("Total Harta Tahun Sebelumnya"), 0, 0)
        source_layout.addWidget(self.harta_prev_value, 0, 1)
        source_layout.addWidget(QLabel("Total Harta Tahun Berjalan"), 0, 2)
        source_layout.addWidget(self.harta_now_value, 0, 3)
        source_layout.addWidget(QLabel("Total Utang Tahun Sebelumnya"), 1, 0)
        source_layout.addWidget(self.utang_prev_edit, 1, 1)
        source_layout.addWidget(QLabel("Total Utang Tahun Berjalan"), 1, 2)
        source_layout.addWidget(self.utang_now_edit, 1, 3)
        source_layout.setColumnStretch(0, 1)
        source_layout.setColumnStretch(2, 1)
        content_layout.addWidget(source_card)

        analysis_card = QFrame(objectName="card")
        analysis_layout = QVBoxLayout(analysis_card)
        analysis_layout.setContentsMargins(20, 16, 20, 18)
        analysis_layout.setSpacing(10)
        heading = QLabel("ANALISIS")
        heading.setObjectName("sectionTitle")
        analysis_layout.addWidget(heading)

        self.reconciliation_table = QTableWidget(8, 4)
        self.reconciliation_table.setHorizontalHeaderLabels(
            ["KODE", "URAIAN", "SUMBER", "NILAI"]
        )
        self.reconciliation_table.verticalHeader().setVisible(False)
        self.reconciliation_table.setAlternatingRowColors(True)
        self.reconciliation_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.reconciliation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.reconciliation_table.setWordWrap(False)
        self.reconciliation_table.itemChanged.connect(
            self._on_reconciliation_analysis_item_changed
        )
        optimize_table_interaction(
            self.reconciliation_table,
            column_widths={0: 65, 1: 330, 2: 260, 3: 180},
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self.reconciliation_table.setMinimumHeight(320)
        analysis_layout.addWidget(self.reconciliation_table)
        content_layout.addWidget(analysis_card)

        income_card = QFrame(objectName="card")
        income_layout = QVBoxLayout(income_card)
        income_layout.setContentsMargins(20, 16, 20, 18)
        income_layout.setSpacing(10)
        income_heading = QLabel("REKONSILIASI PENGHASILAN")
        income_heading.setObjectName("sectionTitle")
        income_layout.addWidget(income_heading)

        self.reconciliation_income_table = QTableWidget(5, 3)
        self.reconciliation_income_table.setHorizontalHeaderLabels(
            ["URAIAN", "SUMBER", "NILAI"]
        )
        self.reconciliation_income_table.verticalHeader().setVisible(False)
        self.reconciliation_income_table.setAlternatingRowColors(True)
        self.reconciliation_income_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.reconciliation_income_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.reconciliation_income_table.setWordWrap(False)
        self.reconciliation_income_table.itemChanged.connect(
            self._on_reconciliation_income_item_changed
        )
        optimize_table_interaction(
            self.reconciliation_income_table,
            column_widths={0: 390, 1: 290, 2: 180},
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self.reconciliation_income_table.setMinimumHeight(215)
        income_layout.addWidget(self.reconciliation_income_table)

        self.save_reconciliation_button = QPushButton("Simpan Analisis")
        self.save_reconciliation_button.setObjectName("primaryButton")
        self.save_reconciliation_button.setMinimumWidth(160)
        self.save_reconciliation_button.setEnabled(False)
        self.save_reconciliation_button.clicked.connect(self.save_bupot_changes)
        income_layout.addWidget(self.save_reconciliation_button, alignment=Qt.AlignLeft)
        content_layout.addWidget(income_card)
        content_layout.addStretch()

        self.reconciliation_scroll_area = QScrollArea()
        self.reconciliation_scroll_area.setObjectName("reconciliationScrollArea")
        self.reconciliation_scroll_area.setWidgetResizable(True)
        self.reconciliation_scroll_area.setFrameShape(QFrame.NoFrame)
        self.reconciliation_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.reconciliation_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.reconciliation_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.reconciliation_scroll_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.reconciliation_scroll_area.setWidget(content)
        optimize_scroll_area(self.reconciliation_scroll_area, vertical_step=24)

        # Harta, PPh, Analisis Rekonsiliasi, Riwayat Audit.
        self.tabs.insertTab(
            2,
            self.reconciliation_scroll_area,
            "Analisis Penghasilan vs Harta",
        )

        self._render_reconciliation()
        self._refresh_bupot_actions()

    @staticmethod
    def _read_only_field():
        edit = QLineEdit("0")
        edit.setReadOnly(True)
        edit.setObjectName("readOnlyField")
        edit.setAlignment(Qt.AlignRight)
        edit.setMinimumHeight(34)
        return edit

    @staticmethod
    def _money_edit():
        edit = QLineEdit("0")
        edit.setAlignment(Qt.AlignRight)
        edit.setMinimumHeight(34)
        return edit

    def _harta_totals_for_reconciliation(self):
        rows = self.harta_current_rows or self.harta_original_rows
        previous = sum(float(row.nilai_tahun_sebelumnya or 0) for row in rows)
        current = sum(float(row.nilai_tahun_berjalan or 0) for row in rows)
        return previous, current

    def _calculate_reconciliation(self):
        harta_prev, harta_now = self._harta_totals_for_reconciliation()
        total_netto = sum(
            self._money_value(row, self.BUPOT_NETTO_COLUMN)
            for row in range(self.bupot_table.rowCount())
        )

        domestic = (
            float(self._other_income_state.get("domestic_other_dpp", 0.0))
            if self._other_income_state.get("domestic_other_enabled")
            else 0.0
        )
        final_result = calculate_final_other_income(self._final_other_income_rows)
        final_detail_pph = sum(float(row.pph) for row in final_result.rows)

        pph_terutang = 0.0
        if self._last_pph_calculation is not None:
            pph_terutang = float(self._last_pph_calculation.pph_terutang)

        umkm_bruto = sum(float(value) for value in self._umkm_bruto)
        umkm_setor = sum(float(value) for value in self._umkm_pph_setor)

        result = calculate_evy_reconciliation(
            total_harta_sebelumnya=harta_prev,
            total_harta_berjalan=harta_now,
            total_utang_sebelumnya=self._reconciliation_manual["utang_sebelumnya"],
            total_utang_berjalan=self._reconciliation_manual["utang_berjalan"],
            status_ptkp=self._status_ptkp,
            pph_umkm_setor=umkm_setor,
            pph21_terutang=pph_terutang,
            sewa_pph=self._other_income_state.get("sewa_pph", 0.0),
            honor_pph=self._other_income_state.get("honor_pph", 0.0),
            final_other_pph_subtotal=final_result.total_pph,
            final_other_pph_detail=final_detail_pph,
            pengeluaran_lain_lain=self._reconciliation_manual["pengeluaran_lain_lain"],
            kerugian_keuntungan_penjualan_aset=self._reconciliation_manual[
                "kerugian_keuntungan_penjualan_aset"
            ],
            utang_baru_atas_kredit=self._reconciliation_manual["utang_baru_atas_kredit"],
            harta_baru_dari_kredit=self._reconciliation_manual["harta_baru_dari_kredit"],
            penghasilan_bruto_umkm=umkm_bruto,
            penambahan_penghasilan_bruto_umkm=self._reconciliation_manual[
                "penambahan_penghasilan_bruto_umkm"
            ],
            margin_usaha=self._reconciliation_manual["margin_usaha"],
            netto_bupot=total_netto,
            domestic_other=domestic,
            pekerjaan_bebas_dpp=self._other_income_state.get("pekerjaan_bebas_dpp", 0.0),
            prive_dpp=self._other_income_state.get("prive_dpp", 0.0),
            hibah_warisan_dpp=self._other_income_state.get("hibah_warisan_dpp", 0.0),
            sewa_dpp=self._other_income_state.get("sewa_dpp", 0.0),
            honor_dpp=self._other_income_state.get("honor_dpp", 0.0),
            final_other_dpp=final_result.total_dpp,
        )
        self._last_reconciliation = result
        return result

    def _render_reconciliation(self):
        if not hasattr(self, "reconciliation_table"):
            return
        result = self._calculate_reconciliation()
        self._rendering_reconciliation = True
        try:
            self.harta_prev_value.setText(
                self._format_bupot_money(result.total_harta_sebelumnya)
            )
            self.harta_now_value.setText(
                self._format_bupot_money(result.total_harta_berjalan)
            )
            self.utang_prev_edit.setText(
                self._format_bupot_money(self._reconciliation_manual["utang_sebelumnya"])
            )
            self.utang_now_edit.setText(
                self._format_bupot_money(self._reconciliation_manual["utang_berjalan"])
            )

            analysis_rows = (
                ("a", "Naik/Turun Harta dan Utang", "Otomatis Harta & Utang", result.naik_turun_harta_utang, False),
                ("b", "Biaya Hidup Setahun", f"Status PTKP {self._status_ptkp}", result.biaya_hidup_setahun, False),
                ("c", "Pajak-pajak", "Formula SIMULASI I Evy", result.pajak_pajak, False),
                ("d", "Pengeluaran lain-lain", "Manual", result.pengeluaran_lain_lain, True),
                ("e", "Kerugian (Keuntungan) penjualan aset", "Manual", result.kerugian_keuntungan_penjualan_aset, True),
                ("f", "Utang baru atas kredit", "Manual", result.utang_baru_atas_kredit, True),
                ("g", "Harta baru dari kredit", "Manual (dikurangkan)", result.harta_baru_dari_kredit, True),
                ("", "TOTAL PENGELUARAN PER TAHUN", "a+b+c+d+e+f-g", result.total_pengeluaran, False),
            )
            with suspended_updates(self.reconciliation_table):
                self.reconciliation_table.blockSignals(True)
                try:
                    for row, (code, caption, source, value, editable) in enumerate(analysis_rows):
                        values = (code, caption, source, self._format_bupot_money(value))
                        for column, text in enumerate(values):
                            item = QTableWidgetItem(str(text))
                            if column != 3 or not editable:
                                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                            if row == 7:
                                font = item.font()
                                font.setBold(True)
                                item.setFont(font)
                            self.reconciliation_table.setItem(row, column, item)
                finally:
                    self.reconciliation_table.blockSignals(False)

            income_rows = (
                ("Penghasilan Bruto UMKM", "Otomatis dari tabel UMKM", result.penghasilan_bruto_umkm, False),
                ("Penambahan Penghasilan Bruto UMKM", "Manual", result.penambahan_penghasilan_bruto_umkm, True),
                ("Margin Usaha", "Manual / Tarif NPPN", self._format_rate(result.margin_usaha), True),
                ("Penghasilan Netto", "Formula SIMULASI I Evy", result.penghasilan_netto, False),
                ("Selisih Total Pengeluaran vs Penghasilan Netto", "Penghasilan Netto - Total Pengeluaran", result.selisih_pengeluaran_vs_penghasilan, False),
            )
            with suspended_updates(self.reconciliation_income_table):
                self.reconciliation_income_table.blockSignals(True)
                try:
                    for row, (caption, source, value, editable) in enumerate(income_rows):
                        self.reconciliation_income_table.setItem(row, 0, QTableWidgetItem(caption))
                        self.reconciliation_income_table.setItem(row, 1, QTableWidgetItem(source))
                        text = value if row == 2 else self._format_bupot_money(value)
                        value_item = QTableWidgetItem(str(text))
                        if not editable:
                            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                        if row in {3, 4}:
                            font = value_item.font()
                            font.setBold(True)
                            value_item.setFont(font)
                        self.reconciliation_income_table.setItem(row, 2, value_item)
                        for column in (0, 1):
                            item = self.reconciliation_income_table.item(row, column)
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                finally:
                    self.reconciliation_income_table.blockSignals(False)
        finally:
            self._rendering_reconciliation = False

        status = "SEIMBANG" if abs(result.selisih_pengeluaran_vs_penghasilan) < 0.5 else "BELUM SEIMBANG"
        self.reconciliation_status.setText(
            f"{status} • Total Pengeluaran Rp {self._format_bupot_money(result.total_pengeluaran)} • "
            f"Penghasilan Netto Rp {self._format_bupot_money(result.penghasilan_netto)} • "
            f"Selisih Rp {self._format_bupot_money(result.selisih_pengeluaran_vs_penghasilan)}"
        )
        self._refresh_reconciliation_actions()

    def _on_reconciliation_field_finished(self, key: str):
        if self._rendering_reconciliation:
            return
        edit = self.utang_prev_edit if key == "utang_sebelumnya" else self.utang_now_edit
        previous = float(self._reconciliation_manual.get(key, 0.0))
        try:
            value = self._parse_bupot_money(edit.text())
            if value < 0:
                raise ValueError("negative")
        except ValueError:
            value = previous
            self.toast_notification.show_message(
                "Nilai Utang tidak valid. Gunakan angka positif.", "warning", 3600
            )
        self._reconciliation_manual[key] = float(value)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _on_reconciliation_analysis_item_changed(self, item: QTableWidgetItem):
        if self._rendering_reconciliation or item is None or item.column() != 3:
            return
        key = self.ANALYSIS_MANUAL_ROW_KEYS.get(item.row())
        if key is None:
            return
        previous = float(self._reconciliation_manual.get(key, 0.0))
        try:
            value = self._parse_bupot_money(item.text())
            if key in {"utang_baru_atas_kredit", "harta_baru_dari_kredit"} and value < 0:
                raise ValueError("negative")
        except ValueError:
            value = previous
            self.toast_notification.show_message(
                "Nilai Analisis tidak valid.", "warning", 3600
            )
        self._reconciliation_manual[key] = float(value)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _on_reconciliation_income_item_changed(self, item: QTableWidgetItem):
        if self._rendering_reconciliation or item is None or item.column() != 2:
            return
        row = item.row()
        if row == 1:
            key = "penambahan_penghasilan_bruto_umkm"
            previous = float(self._reconciliation_manual[key])
            try:
                value = self._parse_bupot_money(item.text())
                if value < 0:
                    raise ValueError("negative")
            except ValueError:
                value = previous
                self.toast_notification.show_message(
                    "Penambahan Bruto UMKM harus berupa angka positif.", "warning", 3600
                )
        elif row == 2:
            key = "margin_usaha"
            previous = float(self._reconciliation_manual[key])
            try:
                value = self._parse_rate(item.text())
                if value < 0:
                    raise ValueError("negative")
            except ValueError:
                value = previous
                self.toast_notification.show_message(
                    "Margin Usaha tidak valid. Contoh: 20% atau 20.", "warning", 3600
                )
        else:
            return
        self._reconciliation_manual[key] = float(value)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _load_pph_state_for_current_wp(self):
        super()._load_pph_state_for_current_wp()
        if not hasattr(self, "reconciliation_table"):
            return

        manual = self._default_reconciliation_manual()
        npwp, year = self._current_pph_identity()
        if npwp and year:
            try:
                persisted = self.pph_state_store.load(npwp, year)
            except Exception:
                persisted = None
            if persisted is not None:
                raw = persisted.components.get("evy_reconciliation")
                if isinstance(raw, dict):
                    for key in manual:
                        if key not in raw:
                            continue
                        try:
                            value = float(raw[key] or 0)
                        except (TypeError, ValueError):
                            continue
                        if key in {
                            "utang_sebelumnya",
                            "utang_berjalan",
                            "utang_baru_atas_kredit",
                            "harta_baru_dari_kredit",
                            "penambahan_penghasilan_bruto_umkm",
                            "margin_usaha",
                        }:
                            value = max(0.0, value)
                        manual[key] = value

        self._reconciliation_manual = manual
        self._saved_reconciliation_manual = deepcopy(manual)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _clear_bupot_working_state(self):
        super()._clear_bupot_working_state()
        self._reconciliation_manual = self._default_reconciliation_manual()
        self._saved_reconciliation_manual = deepcopy(self._reconciliation_manual)
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def _has_unsaved_reconciliation_changes(self):
        return self._reconciliation_manual != self._saved_reconciliation_manual

    def _has_unsaved_pph_component_changes(self) -> bool:
        return (
            super()._has_unsaved_pph_component_changes()
            or self._has_unsaved_reconciliation_changes()
        )

    def _refresh_reconciliation_actions(self):
        if not hasattr(self, "save_reconciliation_button"):
            return
        npwp, year = self._current_pph_identity()
        self.save_reconciliation_button.setEnabled(
            bool(npwp and year) and self._has_unsaved_reconciliation_changes()
        )

    def _refresh_bupot_actions(self):
        super()._refresh_bupot_actions()
        if hasattr(self, "save_reconciliation_button"):
            self._refresh_reconciliation_actions()

    def _refresh_pph_status(self):
        super()._refresh_pph_status()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def _render_umkm_table(self):
        super()._render_umkm_table()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def _sync_other_income_to_summary(self):
        super()._sync_other_income_to_summary()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def _on_ptkp_status_changed(self, index: int):
        super()._on_ptkp_status_changed(index)
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def _on_harta_item_changed(self, item: QTableWidgetItem):
        super()._on_harta_item_changed(item)
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def add_harta_row(self):
        super().add_harta_row()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()

    def remove_selected_harta_rows(self):
        result = super().remove_selected_harta_rows()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()
        return result

    def reset_harta_to_import(self):
        result = super().reset_harta_to_import()
        if hasattr(self, "reconciliation_table"):
            self._render_reconciliation()
        return result

    def save_bupot_changes(self):
        # Simpan seluruh Stage 1-6 terlebih dahulu, lalu tambahkan state Stage 7
        # ke components_json tanpa mengubah skema SQLite.
        result = super().save_bupot_changes()
        if result is None or self._bupot_last_save_error:
            return result

        npwp, year = self._current_pph_identity()
        if not npwp or not year:
            return result

        try:
            persisted = self.pph_state_store.load(npwp, year)
            components = dict(persisted.components if persisted is not None else {})
            components["evy_reconciliation"] = {
                key: float(value)
                for key, value in self._reconciliation_manual.items()
            }
            result = self.pph_state_store.save(
                npwp=npwp,
                tahun_pajak=year,
                bupot_rows=self._snapshot_bupot_rows(),
                components=components,
            )
        except Exception as exc:
            self._bupot_last_save_error = str(exc)
            self.toast_notification.show_message(
                "Worksheet PPh tersimpan, tetapi Analisis Rekonsiliasi gagal disimpan.",
                "error",
                3600,
            )
            return None

        self._bupot_last_save_result = result
        self._saved_reconciliation_manual = deepcopy(self._reconciliation_manual)
        self._refresh_bupot_actions()
        self.toast_notification.show_message(
            "Analisis Penghasilan vs Harta tersimpan ke database.", "success"
        )
        return result
