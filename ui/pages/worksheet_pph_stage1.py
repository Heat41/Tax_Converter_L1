from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from ui.pages.worksheet_notifications import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_table_interaction


class WorksheetPage(BaseWorksheetPage):
    """Stage awal Worksheet Penghasilan & PPh 2025.

    Fokus pertama adalah Bupot manual: BRUTO dan PENGURANG diinput user,
    sedangkan NETTO dihitung otomatis. Perhitungan PPh Tahunan yang lebih luas
    akan dibangun di atas fondasi ini secara bertahap.
    """

    BUPOT_COLUMN_WIDTHS = {
        0: 55,
        1: 150,
        2: 190,
        3: 220,
        4: 140,
        5: 140,
        6: 140,
    }

    BUPOT_MONEY_COLUMNS = {4, 5}
    BUPOT_NETTO_COLUMN = 6

    def __init__(self, parent=None):
        self._rendering_bupot = False
        super().__init__(parent)
        self._install_pph_stage1()

    def _install_pph_stage1(self):
        self.pph_status = QLabel()
        self.pph_status.setObjectName("mutedLabel")
        self.pph_status.setWordWrap(True)

        info_card = self.pph_tab.layout().itemAt(0).widget()
        if info_card is not None and info_card.layout() is not None:
            info_card.layout().addWidget(self.pph_status)

        self.bupot_table.itemChanged.connect(self._on_bupot_item_changed)
        optimize_table_interaction(
            self.bupot_table,
            column_widths=self.BUPOT_COLUMN_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        self._refresh_pph_status()
        self._refresh_bupot_actions()

    def _add_bupot_row(self):
        self._rendering_bupot = True
        self.bupot_table.blockSignals(True)
        try:
            super()._add_bupot_row()
            row = self.bupot_table.rowCount() - 1
            if row < 0:
                return

            for column in range(1, 6):
                item = self.bupot_table.item(row, column)
                if item is None:
                    item = QTableWidgetItem("0" if column in self.BUPOT_MONEY_COLUMNS else "")
                    self.bupot_table.setItem(row, column, item)
                if column in self.BUPOT_MONEY_COLUMNS:
                    item.setData(Qt.UserRole, 0.0)

            netto_item = self.bupot_table.item(row, self.BUPOT_NETTO_COLUMN)
            if netto_item is None:
                netto_item = QTableWidgetItem("0")
                self.bupot_table.setItem(row, self.BUPOT_NETTO_COLUMN, netto_item)
            netto_item.setFlags(netto_item.flags() & ~Qt.ItemIsEditable)
            netto_item.setData(Qt.UserRole, 0.0)
        finally:
            self.bupot_table.blockSignals(False)
            self._rendering_bupot = False

        self.bupot_table.selectRow(self.bupot_table.rowCount() - 1)
        self._refresh_pph_status()
        self._refresh_bupot_actions()

    def _remove_bupot_row(self):
        super()._remove_bupot_row()
        self._refresh_pph_status()
        self._refresh_bupot_actions()

    def _on_bupot_item_changed(self, item: QTableWidgetItem):
        if self._rendering_bupot or item is None:
            return
        if item.column() not in self.BUPOT_MONEY_COLUMNS:
            return

        row = item.row()
        previous = item.data(Qt.UserRole)
        try:
            value = self._parse_bupot_money(item.text())
        except ValueError:
            value = float(previous or 0.0)
            self.bupot_table.blockSignals(True)
            try:
                item.setText(self._format_bupot_money(value))
            finally:
                self.bupot_table.blockSignals(False)
            self.toast_notification.show_message(
                "Nilai Bupot tidak valid. Gunakan angka, misalnya 1.500.000.",
                "warning",
            )
            return

        self.bupot_table.blockSignals(True)
        try:
            item.setData(Qt.UserRole, value)
            item.setText(self._format_bupot_money(value))
            self._recalculate_bupot_row(row)
        finally:
            self.bupot_table.blockSignals(False)

        self._refresh_pph_status()

    def _recalculate_bupot_row(self, row: int):
        bruto = self._money_value(row, 4)
        pengurang = self._money_value(row, 5)
        netto = bruto - pengurang

        item = self.bupot_table.item(row, self.BUPOT_NETTO_COLUMN)
        if item is None:
            item = QTableWidgetItem()
            self.bupot_table.setItem(row, self.BUPOT_NETTO_COLUMN, item)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setData(Qt.UserRole, netto)
        item.setText(self._format_bupot_money(netto))

    def _money_value(self, row: int, column: int) -> float:
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
            return self._parse_bupot_money(item.text())
        except ValueError:
            return 0.0

    def _refresh_pph_status(self):
        rows = self.bupot_table.rowCount()
        total_bruto = sum(self._money_value(row, 4) for row in range(rows))
        total_pengurang = sum(self._money_value(row, 5) for row in range(rows))
        total_netto = sum(self._money_value(row, 6) for row in range(rows))
        self.pph_status.setText(
            f"{rows} baris Bupot • Total Bruto Rp {self._format_bupot_money(total_bruto)} • "
            f"Total Pengurang Rp {self._format_bupot_money(total_pengurang)} • "
            f"Total Netto Rp {self._format_bupot_money(total_netto)}"
        )

    def _refresh_bupot_actions(self):
        self.remove_bupot_button.setEnabled(self.bupot_table.rowCount() > 0)

    @staticmethod
    def _parse_bupot_money(value: object) -> float:
        text = str(value or "").strip()
        if not text:
            return 0.0
        cleaned = text.replace("Rp", "").replace("rp", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                cleaned = "".join(parts)
        elif "," in cleaned:
            tail = cleaned.rsplit(",", 1)[-1]
            cleaned = cleaned.replace(",", ".") if len(tail) <= 2 else cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError as exc:
            raise ValueError("angka Bupot tidak valid") from exc

    @staticmethod
    def _format_bupot_money(value: object) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        if number == 0:
            return "0"
        return f"{number:,.0f}".replace(",", ".")
