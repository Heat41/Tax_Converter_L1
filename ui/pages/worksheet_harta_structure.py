from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from ui.pages.worksheet_page import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Lapisan editor struktur untuk Worksheet Harta.

    Menambahkan kemampuan tambah/hapus baris pada mode Edited / Current tanpa
    mengubah Original Import. Setiap baris Current menyimpan referensi indeks
    baris Original agar perubahan tetap dapat dibandingkan walau urutan baris
    berubah akibat penghapusan atau penambahan.
    """

    def __init__(self, parent=None):
        self.harta_origin_indices = []
        self.harta_saved_origin_indices = []
        super().__init__(parent)
        self._install_structure_actions()
        self._refresh_harta_actions()

    def _install_structure_actions(self):
        self.add_harta_button = QPushButton("+ Tambah Baris")
        self.add_harta_button.setObjectName("secondaryButton")
        self.add_harta_button.setEnabled(False)

        self.remove_harta_button = QPushButton("Hapus Baris")
        self.remove_harta_button.setObjectName("secondaryButton")
        self.remove_harta_button.setEnabled(False)

        # Layout Harta: info card, toolbar, tabel.
        toolbar_item = self.harta_tab.layout().itemAt(1)
        toolbar = toolbar_item.layout() if toolbar_item is not None else None
        if toolbar is not None:
            toolbar.insertWidget(2, self.add_harta_button)
            toolbar.insertWidget(3, self.remove_harta_button)

        self.add_harta_button.clicked.connect(self.add_harta_row)
        self.remove_harta_button.clicked.connect(self.remove_selected_harta_rows)
        self.harta_table.itemSelectionChanged.connect(self._refresh_harta_actions)

    def load_harta_preview(self, pipeline_result):
        super().load_harta_preview(pipeline_result)
        if pipeline_result is not None and getattr(pipeline_result, "worksheet_rows", None):
            self.harta_origin_indices = list(range(len(self.harta_original_rows)))
            self.harta_saved_origin_indices = list(self.harta_origin_indices)
        else:
            self.harta_origin_indices = []
            self.harta_saved_origin_indices = []
        self._refresh_harta_actions()

    def clear_harta_preview(self):
        super().clear_harta_preview()
        self.harta_origin_indices = []
        self.harta_saved_origin_indices = []
        if hasattr(self, "add_harta_button"):
            self._refresh_harta_actions()

    def _show_harta_mode(self, mode: str):
        super()._show_harta_mode(mode)
        self._refresh_harta_actions()

    def add_harta_row(self):
        if self.harta_mode != "current" or self.harta_pipeline_result is None:
            return

        year = self.harta_pipeline_result.current_year
        try:
            acquisition_year = int(year) if year else 2025
        except (TypeError, ValueError):
            acquisition_year = 2025

        new_row = WorksheetHartaRow(
            nomor=len(self.harta_current_rows) + 1,
            kode_eform="",
            kode_ct="",
            nama_harta="",
            nomor_akun_keterangan="",
            atas_nama="",
            nama_bank="",
            tahun_perolehan=acquisition_year,
            nilai_tahun_sebelumnya=0.0,
            nilai_tahun_berjalan=0.0,
        )
        self.harta_current_rows.append(new_row)
        self.harta_origin_indices.append(None)
        self._renumber_current_rows()
        self._render_harta_rows(self.harta_current_rows)

        new_index = len(self.harta_current_rows) - 1
        self.harta_table.selectRow(new_index)
        self.harta_table.scrollToItem(self.harta_table.item(new_index, 1))
        self._refresh_harta_actions()
        self._update_harta_status()

    def remove_selected_harta_rows(self):
        if self.harta_mode != "current" or not self.harta_current_rows:
            return 0

        selected_rows = sorted(
            {index.row() for index in self.harta_table.selectedIndexes()},
            reverse=True,
        )
        if not selected_rows:
            return 0

        removed = 0
        for row_index in selected_rows:
            if 0 <= row_index < len(self.harta_current_rows):
                del self.harta_current_rows[row_index]
                del self.harta_origin_indices[row_index]
                removed += 1

        if removed:
            self._renumber_current_rows()
            self._render_harta_rows(self.harta_current_rows)
            self._refresh_harta_actions()
            self._update_harta_status()
        return removed

    def _renumber_current_rows(self):
        self.harta_current_rows = [
            replace(row, nomor=index + 1)
            for index, row in enumerate(self.harta_current_rows)
        ]

    def _original_index_for_current(self, row_index: int):
        if row_index < 0 or row_index >= len(self.harta_origin_indices):
            return None
        return self.harta_origin_indices[row_index]

    def _cell_changed_from_original(self, row_index: int, column_index: int) -> bool:
        if row_index < 0 or row_index >= len(self.harta_current_rows):
            return False

        original_index = self._original_index_for_current(row_index)
        if original_index is None:
            # Baris manual baru ditandai seluruh kolom editable-nya.
            return column_index > 0
        if original_index < 0 or original_index >= len(self.harta_original_rows):
            return True

        field_name = self.HARTA_FIELDS[column_index]
        return getattr(
            self.harta_original_rows[original_index], field_name
        ) != getattr(self.harta_current_rows[row_index], field_name)

    def _count_changed_cells(self) -> int:
        total = 0
        for row_index, original_index in enumerate(self.harta_origin_indices):
            if original_index is None:
                continue
            for column_index in range(1, len(self.HARTA_FIELDS)):
                if self._cell_changed_from_original(row_index, column_index):
                    total += 1
        return total

    def _count_added_rows(self) -> int:
        return sum(index is None for index in self.harta_origin_indices)

    def _count_deleted_rows(self) -> int:
        present_original = {
            index for index in self.harta_origin_indices if index is not None
        }
        return max(0, len(self.harta_original_rows) - len(present_original))

    def _has_any_harta_changes(self) -> bool:
        return bool(
            self._count_changed_cells()
            or self._count_added_rows()
            or self._count_deleted_rows()
        )

    def _has_unsaved_harta_changes(self) -> bool:
        return (
            self.harta_current_rows != self.harta_saved_rows
            or self.harta_origin_indices != self.harta_saved_origin_indices
        )

    def _refresh_harta_actions(self):
        has_pipeline = self.harta_pipeline_result is not None
        current_mode = self.harta_mode == "current"
        has_rows = bool(self.harta_current_rows)

        if hasattr(self, "add_harta_button"):
            self.add_harta_button.setEnabled(has_pipeline and current_mode)
        if hasattr(self, "remove_harta_button"):
            has_selection = bool(self.harta_table.selectedIndexes())
            self.remove_harta_button.setEnabled(
                has_pipeline and current_mode and has_rows and has_selection
            )

        self.reset_harta_button.setEnabled(
            has_pipeline and self._has_any_harta_changes()
        )
        self.save_harta_button.setEnabled(
            has_pipeline
            and current_mode
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
        edited = self._count_changed_cells()
        added = self._count_added_rows()
        deleted = self._count_deleted_rows()

        suffix = ""
        if self.harta_mode == "current":
            if saved:
                suffix = " • perubahan tersimpan pada sesi worksheet"
            elif self._has_unsaved_harta_changes():
                suffix = " • ada perubahan belum disimpan"
            elif self._has_any_harta_changes():
                suffix = " • koreksi tersimpan pada sesi worksheet"

        self.harta_status.setText(
            f"Mode {label} • {len(self.harta_current_rows)} baris Harta • "
            f"Tahun {year} • {edited} sel dikoreksi • "
            f"{added} baris ditambah • {deleted} baris dihapus{suffix}"
        )

    def save_harta_changes(self):
        if self.harta_mode != "current" or self.harta_pipeline_result is None:
            return
        self.harta_saved_rows = list(self.harta_current_rows)
        self.harta_saved_origin_indices = list(self.harta_origin_indices)
        self._refresh_harta_actions()
        self._update_harta_status(saved=True)

    def reset_harta_to_import(self):
        if not self.harta_original_rows:
            return
        self.harta_current_rows = list(self.harta_original_rows)
        self.harta_origin_indices = list(range(len(self.harta_original_rows)))
        self._render_harta_rows(self.harta_current_rows)
        self._refresh_harta_actions()
        self._update_harta_status()
