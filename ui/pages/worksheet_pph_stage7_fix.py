from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QTableWidgetItem,
)

from core.worksheet_pph_state import WorksheetBupotRow
from core.worksheet_sorting import sort_bupot_rows, sort_harta_rows

from ui.pages.worksheet_pph_stage7 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_scroll_area


class WorksheetPage(BaseWorksheetPage):
    """Perbaikan Stage 7 untuk alur Worksheet produksi.

    Perbaikan:
    - field Penghasilan Dalam Negeri Lainnya dan Zakat pada Ringkasan PPh selalu
      mengikuti state yang benar-benar dipakai engine kalkulasi;
    - Total Harta Tahun Sebelumnya dapat diisi sebagai baseline manual bila file
      tahun berjalan tidak membawa nilai tahun sebelumnya;
    - rekonsiliasi memberi informasi sumber baseline agar nilai 0 yang sebenarnya
      berarti 'belum tersedia' tidak dianggap sebagai baseline valid;
    - hasil impor workbook langsung mengisi tabel Bupot dari hasil parsing workbook,
      sehingga UI tidak bergantung pada siklus reload database;
    - tabel Harta / SIMULASI I menyediakan viewport minimal 10 baris data;
    - halaman Harta / SIMULASI I memiliki vertical page scrolling seperti halaman
      Penghasilan dan Analisis, sehingga toolbar dan tabel tetap dapat diakses pada
      tinggi window yang terbatas.
    """

    HARTA_VISIBLE_ROWS = 10
    HARTA_ROW_HEIGHT = 34

    @staticmethod
    def _default_reconciliation_manual():
        state = BaseWorksheetPage._default_reconciliation_manual()
        state["harta_sebelumnya_override"] = 0.0
        return state

    def __init__(self, parent=None):
        super().__init__(parent)

        self.harta_prev_value.setReadOnly(False)
        self.harta_prev_value.setObjectName("")
        self.harta_prev_value.setToolTip(
            "Isi Total Harta Tahun Sebelumnya bila baseline tidak tersedia dari file Kertas Kerja. "
            "Masukkan 0 untuk menggunakan nilai otomatis."
        )
        self.harta_prev_value.editingFinished.connect(
            self._on_harta_previous_baseline_finished
        )
        self._repolish_widget(self.harta_prev_value)
        self._configure_harta_visible_rows()
        self._install_harta_page_scrolling()
        self._upgrade_bupot_table_to_rekap_fields()
        self._render_reconciliation()
        self._recalculate_pph_summary()

    BUPOT_HEADERS = (
        "NO",
        "JENIS BUPOT",
        "NO BUKPOT",
        "MASA",
        "TAHUN",
        "SIFAT",
        "STATUS",
        "NPWP PENERIMA",
        "NAMA PENERIMA",
        "FASILITAS",
        "JENIS PPH",
        "KOP",
        "BRUTO",
        "DPP PERSEN",
        "TARIF",
        "PENGURANG BRUTO",
        "PPH",
        "BUKTI",
        "NO BUKTI",
        "TANGGAL BUKTI",
        "NPWP PEMOTONG",
        "NAMA PEMOTONG",
        "TANGGAL PEMOTONGAN",
        "MEKANISME SP2D",
        "NO SP2D",
    )
    REKAP_BRUTO_COLUMN = 12
    REKAP_DPP_COLUMN = 13
    REKAP_TARIF_COLUMN = 14
    REKAP_PENGURANG_COLUMN = 15
    REKAP_PPH_COLUMN = 16
    REKAP_MONEY_COLUMNS = {12, 15, 16}
    REKAP_RATE_COLUMNS = {13, 14}

    def _upgrade_bupot_table_to_rekap_fields(self):
        if not hasattr(self, "bupot_table"):
            return

        self.bupot_table.blockSignals(True)
        try:
            self.bupot_table.clearContents()
            self.bupot_table.setRowCount(0)
            self.bupot_table.setColumnCount(len(self.BUPOT_HEADERS))
            self.bupot_table.setHorizontalHeaderLabels(self.BUPOT_HEADERS)
            self.bupot_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.bupot_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            widths = {
                0: 55, 1: 110, 2: 145, 3: 70, 4: 75, 5: 110, 6: 100,
                7: 170, 8: 190, 9: 145, 10: 100, 11: 100,
                12: 125, 13: 95, 14: 85, 15: 145, 16: 125,
                17: 145, 18: 190, 19: 125, 20: 170, 21: 190,
                22: 135, 23: 135, 24: 140,
            }
            for column, width in widths.items():
                self.bupot_table.setColumnWidth(column, width)
        finally:
            self.bupot_table.blockSignals(False)

        self._load_pph_state_for_current_wp()

    def _render_bupot_rows(self, rows):
        if not hasattr(self, "bupot_table"):
            return

        rows = sort_bupot_rows(rows)
        self._rendering_bupot = True
        self.bupot_table.blockSignals(True)
        try:
            self.bupot_table.clearContents()
            self.bupot_table.setRowCount(len(rows))

            for row_index, row in enumerate(rows):
                values = (
                    row_index + 1,
                    getattr(row, "jenis", ""),
                    getattr(row, "no_bupot", ""),
                    getattr(row, "masa", ""),
                    getattr(row, "tahun", ""),
                    getattr(row, "sifat", ""),
                    getattr(row, "status", ""),
                    getattr(row, "npwp_penerima", ""),
                    getattr(row, "nama_penerima", ""),
                    getattr(row, "fasilitas", ""),
                    getattr(row, "jenis_pph", ""),
                    getattr(row, "kop", ""),
                    getattr(row, "bruto", 0.0),
                    getattr(row, "dpp_persen", 0.0),
                    getattr(row, "tarif", 0.0),
                    getattr(row, "pengurang", 0.0),
                    getattr(row, "pph_dipotong", 0.0),
                    getattr(row, "bukti", ""),
                    getattr(row, "no_bukti", ""),
                    getattr(row, "tanggal_bukti", ""),
                    getattr(row, "npwp_pemotong", "")
                    or getattr(row, "npwp_pemberi_kerja", ""),
                    getattr(row, "nama_pemotong", ""),
                    getattr(row, "tanggal_pemotongan", ""),
                    getattr(row, "mekanisme_sp2d", ""),
                    getattr(row, "no_sp2d", ""),
                )

                for column, value in enumerate(values):
                    if column in self.REKAP_MONEY_COLUMNS:
                        item = QTableWidgetItem(self._format_bupot_money(value))
                        item.setData(Qt.UserRole, float(value or 0))
                    elif column in self.REKAP_RATE_COLUMNS:
                        item = QTableWidgetItem(self._format_rekap_rate(value))
                        item.setData(Qt.UserRole, float(value or 0))
                    else:
                        item = QTableWidgetItem(str(value or ""))

                    if column == 0:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.bupot_table.setItem(row_index, column, item)
        finally:
            self.bupot_table.blockSignals(False)
            self._rendering_bupot = False

        self._refresh_pph_status()
        self._refresh_bupot_actions()

    def _add_bupot_row(self):
        if not hasattr(self, "bupot_table"):
            return

        self._rendering_bupot = True
        self.bupot_table.blockSignals(True)
        try:
            row = self.bupot_table.rowCount()
            self.bupot_table.insertRow(row)
            for column in range(len(self.BUPOT_HEADERS)):
                if column == 0:
                    item = QTableWidgetItem(str(row + 1))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                elif column in self.REKAP_MONEY_COLUMNS:
                    item = QTableWidgetItem("0")
                    item.setData(Qt.UserRole, 0.0)
                elif column in self.REKAP_RATE_COLUMNS:
                    item = QTableWidgetItem("0")
                    item.setData(Qt.UserRole, 0.0)
                else:
                    item = QTableWidgetItem("")
                self.bupot_table.setItem(row, column, item)
        finally:
            self.bupot_table.blockSignals(False)
            self._rendering_bupot = False

        self.bupot_table.selectRow(self.bupot_table.rowCount() - 1)
        self._validate_and_refresh_bupot()

    def _on_bupot_item_changed(self, item: QTableWidgetItem):
        if self._rendering_bupot or item is None:
            return

        column = item.column()
        if column in self.REKAP_MONEY_COLUMNS:
            previous = item.data(Qt.UserRole)
            try:
                value = self._parse_bupot_money(item.text())
            except ValueError:
                value = float(previous or 0.0)
                self.toast_notification.show_message(
                    "Nilai Bupot tidak valid. Gunakan angka.",
                    "warning",
                    3200,
                )
            self.bupot_table.blockSignals(True)
            try:
                item.setData(Qt.UserRole, value)
                item.setText(self._format_bupot_money(value))
            finally:
                self.bupot_table.blockSignals(False)

        elif column in self.REKAP_RATE_COLUMNS:
            previous = item.data(Qt.UserRole)
            try:
                value = self._parse_rekap_rate(item.text())
            except ValueError:
                value = float(previous or 0.0)
                self.toast_notification.show_message(
                    "DPP Persen / Tarif tidak valid.",
                    "warning",
                    3200,
                )
            self.bupot_table.blockSignals(True)
            try:
                item.setData(Qt.UserRole, value)
                item.setText(self._format_rekap_rate(value))
            finally:
                self.bupot_table.blockSignals(False)

        self._validate_and_refresh_bupot()

    def _snapshot_bupot_rows(self):
        rows = []
        for row in range(self.bupot_table.rowCount()):
            npwp_pemotong = self.pph_state_store.normalize_npwp(
                self._cell_text(row, 20)
            )
            rows.append(
                WorksheetBupotRow(
                    jenis=self._cell_text(row, 1),
                    no_bupot=self._cell_text(row, 2),
                    masa=self._cell_text(row, 3),
                    tahun=self._cell_text(row, 4),
                    sifat=self._cell_text(row, 5),
                    status=self._cell_text(row, 6),
                    npwp_penerima=self.pph_state_store.normalize_npwp(
                        self._cell_text(row, 7)
                    ),
                    nama_penerima=self._cell_text(row, 8),
                    fasilitas=self._cell_text(row, 9),
                    jenis_pph=self._cell_text(row, 10),
                    kop=self._cell_text(row, 11),
                    bruto=self._money_value(row, self.REKAP_BRUTO_COLUMN),
                    dpp_persen=self._rate_value(row, self.REKAP_DPP_COLUMN),
                    tarif=self._rate_value(row, self.REKAP_TARIF_COLUMN),
                    pengurang=self._money_value(row, self.REKAP_PENGURANG_COLUMN),
                    pph_dipotong=self._money_value(row, self.REKAP_PPH_COLUMN),
                    bukti=self._cell_text(row, 17),
                    no_bukti=self._cell_text(row, 18),
                    tanggal_bukti=self._cell_text(row, 19),
                    npwp_pemotong=npwp_pemotong,
                    nama_pemotong=self._cell_text(row, 21),
                    tanggal_pemotongan=self._cell_text(row, 22),
                    mekanisme_sp2d=self._cell_text(row, 23),
                    no_sp2d=self._cell_text(row, 24),
                    npwp_pemberi_kerja=npwp_pemotong,
                )
            )
        return rows

    def _money_value(self, row: int, column: int) -> float:
        if (
            hasattr(self, "bupot_table")
            and self.bupot_table.columnCount() >= len(self.BUPOT_HEADERS)
            and column == 6
        ):
            bruto = super()._money_value(row, self.REKAP_BRUTO_COLUMN)
            pengurang = super()._money_value(row, self.REKAP_PENGURANG_COLUMN)
            return bruto - pengurang
        return super()._money_value(row, column)

    def _row_pph_dipotong(self, row_index: int) -> float:
        return self._money_value(row_index, self.REKAP_PPH_COLUMN)

    def _validate_bupot_rows(self):
        errors = []
        seen = {}

        for row in range(self.bupot_table.rowCount()):
            jenis = self._cell_text(row, 1)
            no_bupot = self._cell_text(row, 2)
            bruto = self._money_value(row, self.REKAP_BRUTO_COLUMN)
            pengurang = self._money_value(row, self.REKAP_PENGURANG_COLUMN)
            pph = self._money_value(row, self.REKAP_PPH_COLUMN)

            if not jenis:
                errors.append((row, 1, "JENIS BUPOT wajib diisi."))
            if not no_bupot:
                errors.append((row, 2, "NO BUKPOT wajib diisi."))
            if bruto < 0:
                errors.append((row, self.REKAP_BRUTO_COLUMN, "BRUTO tidak boleh negatif."))
            if pengurang < 0:
                errors.append((row, self.REKAP_PENGURANG_COLUMN, "PENGURANG BRUTO tidak boleh negatif."))
            if pph < 0:
                errors.append((row, self.REKAP_PPH_COLUMN, "PPH tidak boleh negatif."))

            if no_bupot:
                key = (jenis.casefold(), no_bupot.casefold())
                if key in seen:
                    first = seen[key]
                    errors.append((first, 2, "NO BUKPOT duplikat untuk jenis yang sama."))
                    errors.append((row, 2, "NO BUKPOT duplikat untuk jenis yang sama."))
                else:
                    seen[key] = row

        return errors

    def _apply_bupot_validation(self, errors):
        error_map = {}
        for row, column, message in errors:
            error_map.setdefault((row, column), message)

        self.bupot_table.blockSignals(True)
        try:
            for row in range(self.bupot_table.rowCount()):
                for column in range(1, self.bupot_table.columnCount()):
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

    def _refresh_pph_status(self):
        rows = self.bupot_table.rowCount()
        total_bruto = sum(
            self._money_value(row, self.REKAP_BRUTO_COLUMN)
            for row in range(rows)
        )
        total_pengurang = sum(
            self._money_value(row, self.REKAP_PENGURANG_COLUMN)
            for row in range(rows)
        )
        total_pph = sum(
            self._money_value(row, self.REKAP_PPH_COLUMN)
            for row in range(rows)
        )
        total_netto = total_bruto - total_pengurang
        self._set_bupot_summary_values(
            rows=rows,
            total_bruto=total_bruto,
            total_pengurang=total_pengurang,
            total_netto=total_netto,
            total_pph=total_pph,
        )

    def _rate_value(self, row: int, column: int) -> float:
        item = self.bupot_table.item(row, column)
        if item is None:
            return 0.0
        stored = item.data(Qt.UserRole)
        if stored is not None:
            try:
                return float(stored)
            except (TypeError, ValueError):
                pass
        try:
            return self._parse_rekap_rate(item.text())
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_rekap_rate(value: object) -> float:
        text = str(value or "").strip().replace("%", "").replace(" ", "")
        if not text:
            return 0.0
        text = text.replace(",", ".")
        try:
            number = float(text)
        except ValueError as exc:
            raise ValueError("rate tidak valid") from exc
        if number < 0:
            raise ValueError("rate negatif")
        return number

    @staticmethod
    def _format_rekap_rate(value: object) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        if number == 0:
            return "0"
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.4f}".rstrip("0").rstrip(".")

    def _configure_harta_visible_rows(self):
        header = self.harta_table.horizontalHeader()
        header_height = max(header.height(), header.sizeHint().height())
        scrollbar_height = self.harta_table.horizontalScrollBar().sizeHint().height()
        frame = self.harta_table.frameWidth() * 2
        padding = 8
        target_height = (
            header_height
            + (self.HARTA_VISIBLE_ROWS * self.HARTA_ROW_HEIGHT)
            + scrollbar_height
            + frame
            + padding
        )
        self.harta_table.setMinimumHeight(target_height)

    def _install_harta_page_scrolling(self):
        tab_index = self.tabs.indexOf(self.harta_tab)
        if tab_index < 0:
            return

        tab_text = self.tabs.tabText(tab_index)
        tab_icon = self.tabs.tabIcon(tab_index)
        tab_tooltip = self.tabs.tabToolTip(tab_index)

        self.tabs.removeTab(tab_index)

        self.harta_scroll_area = QScrollArea()
        self.harta_scroll_area.setObjectName("hartaPageScrollArea")
        self.harta_scroll_area.setWidgetResizable(True)
        self.harta_scroll_area.setFrameShape(QFrame.NoFrame)
        self.harta_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.harta_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.harta_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.harta_scroll_area.setMinimumWidth(0)
        self.harta_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.harta_tab.setMinimumWidth(0)
        self.harta_tab.setMinimumHeight(720)
        self.harta_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.harta_scroll_area.setWidget(self.harta_tab)
        optimize_scroll_area(self.harta_scroll_area, vertical_step=24)

        self.tabs.insertTab(tab_index, self.harta_scroll_area, tab_icon, tab_text)
        self.tabs.setTabToolTip(tab_index, tab_tooltip)

    def load_workbook_import_result(self, import_result):
        """Sinkronkan Sheet Tahun, SIMULASI I, dan REVISI ke Worksheet."""
        pipeline = getattr(import_result, "pipeline_result", None)
        if pipeline is not None:
            self.load_harta_preview(pipeline)

        revision_rows = sort_harta_rows(
            getattr(import_result, "revision_harta_rows", []) or []
        )
        if pipeline is not None and revision_rows:
            # SIMULASI I tetap menjadi Original Import. REVISI menjadi kondisi
            # Edited / Current awal, sehingga perbedaan tetap dapat diaudit.
            self.harta_current_rows = list(revision_rows)
            self.harta_saved_rows = list(revision_rows)
            self._refresh_harta_actions()
            self._update_harta_status(saved=True)

        year = int(getattr(import_result, "tahun_pajak", 0) or 0)
        if year:
            pph_container = getattr(self, "pph_scroll_area", None)
            if pph_container is None:
                pph_container = getattr(self, "pph_tab", None)
            pph_index = self.tabs.indexOf(pph_container) if pph_container is not None else -1
            if pph_index < 0:
                for index in range(self.tabs.count()):
                    if "PPh" in self.tabs.tabText(index):
                        pph_index = index
                        break
            if pph_index >= 0:
                self.tabs.setTabText(pph_index, f"Penghasilan & PPh {year}")

        if pipeline is not None and hasattr(self, "_load_pph_state_for_current_wp"):
            self._load_pph_state_for_current_wp()

        if hasattr(self, "toast_notification"):
            revision_note = (
                f" REVISI dimuat sebagai Edited / Current ({len(revision_rows)} Harta)."
                if revision_rows
                else ""
            )
            self.toast_notification.show_message(
                f"Kertas Kerja Tahun {year or '-'} berhasil dimuat.{revision_note}",
                "success",
                3200,
            )

    @staticmethod
    def _repolish_widget(widget):
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _automatic_harta_totals(self):
        rows = self.harta_current_rows or self.harta_original_rows
        previous = sum(float(row.nilai_tahun_sebelumnya or 0) for row in rows)
        current = sum(float(row.nilai_tahun_berjalan or 0) for row in rows)
        return previous, current

    def _harta_totals_for_reconciliation(self):
        automatic_previous, current = self._automatic_harta_totals()
        override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )
        previous = override if override > 0 else automatic_previous
        return previous, current

    def _on_harta_previous_baseline_finished(self):
        if self._rendering_reconciliation:
            return

        automatic_previous, _ = self._automatic_harta_totals()
        previous_override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )
        try:
            value = self._parse_bupot_money(self.harta_prev_value.text())
            if value < 0:
                raise ValueError("negative")
        except ValueError:
            value = previous_override
            self.toast_notification.show_message(
                "Total Harta Tahun Sebelumnya tidak valid. Gunakan angka positif.",
                "warning",
                3600,
            )

        if value <= 0 or (
            automatic_previous > 0 and abs(value - automatic_previous) < 0.5
        ):
            value = 0.0

        self._reconciliation_manual["harta_sebelumnya_override"] = float(value)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _recalculate_pph_summary(self):
        super()._recalculate_pph_summary()

        if not hasattr(self, "pph_auto_values"):
            return
        for key in (
            "penghasilan_neto_lainnya",
            "pengurang_penghasilan_neto",
        ):
            field = self.pph_auto_values.get(key)
            if field is not None:
                field.setText(
                    self._format_bupot_money(
                        self._pph_component_values.get(key, 0.0)
                    )
                )

    def _render_reconciliation(self):
        super()._render_reconciliation()
        if not hasattr(self, "reconciliation_status"):
            return

        automatic_previous, _ = self._automatic_harta_totals()
        override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )

        self.harta_prev_value.setReadOnly(False)
        self.harta_prev_value.setObjectName("")
        self._repolish_widget(self.harta_prev_value)

        base_status = self.reconciliation_status.text()
        if override > 0:
            source = "Baseline Harta tahun sebelumnya: MANUAL"
        elif automatic_previous > 0:
            source = "Baseline Harta tahun sebelumnya: OTOMATIS"
        else:
            source = (
                "⚠ Baseline Harta tahun sebelumnya belum tersedia. "
                "Isi Total Harta Tahun Sebelumnya sebelum menilai hasil rekonsiliasi"
            )
        self.reconciliation_status.setText(f"{source} • {base_status}")
