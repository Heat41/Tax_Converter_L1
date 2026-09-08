from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMessageBox,
)

from ui.pages.worksheet_harta_structure import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Presentation wrapper untuk memperjelas mode dan notifikasi Worksheet Harta."""

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._install_harta_feedback()
        self._optimize_harta_table()

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

    def _optimize_harta_table(self):
        """Kurangi layout recalculation agar scroll/resize window lebih halus."""
        table = self.harta_table
        header = table.horizontalHeader()
        vertical = table.verticalHeader()

        # ResizeToContents mengukur ulang isi sel ketika viewport berubah.
        # Interactive + lebar stabil jauh lebih ringan untuk grid worksheet.
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)
        for column, width in self.HARTA_COLUMN_WIDTHS.items():
            table.setColumnWidth(column, width)

        # Tinggi baris tetap mencegah geometry recalculation selama scrolling.
        vertical.setSectionResizeMode(QHeaderView.Fixed)
        vertical.setDefaultSectionSize(34)
        vertical.setMinimumSectionSize(34)

        # Scroll per-pixel menghindari kesan meloncat/patah per baris atau kolom.
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.horizontalScrollBar().setSingleStep(18)
        table.verticalScrollBar().setSingleStep(18)

        # Grid tidak membutuhkan wrap; elide menjaga render sel tetap ringan.
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.setCornerButtonEnabled(False)

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
            self._show_notice(
                "✓ Data Harta berhasil tersambung. Mode Original Import aktif dan data hanya dapat dilihat.",
                "info",
            )
        else:
            self._hide_notice()

    def clear_harta_preview(self):
        super().clear_harta_preview()
        if hasattr(self, "harta_notice"):
            self._hide_notice()

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
        super().save_harta_changes()
        if had_unsaved:
            self._show_notice(
                f"✓ Perubahan tersimpan pada sesi worksheet. {self._change_summary()} tetap ditandai terhadap Original Import.",
                "success",
            )

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
            "✓ Edited / Current berhasil dikembalikan ke Original Import. Semua koreksi, penambahan, dan penghapusan telah dibatalkan.",
            "success",
        )
