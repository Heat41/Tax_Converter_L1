from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFileDialog, QMessageBox, QPushButton

from core.worksheet_workbook_importer import WorksheetWorkbookImporter
from ui.performance import (
    optimize_scroll_area,
    optimize_table_interaction,
    suspended_updates,
)
from ui.pages.import_coretax_page import ImportCoretaxPage as BaseImportCoretaxPage


class ImportCoretaxPage(BaseImportCoretaxPage):
    """Presentation wrapper untuk state halaman Impor Coretax.

    Selain styling state, halaman ini memancarkan hasil preview Harta agar
    halaman Worksheet dapat memakai hasil pipeline yang sama tanpa menghitung
    ulang data Coretax. Stage 8B.1 juga menambahkan jalur impor Kertas Kerja
    yang sudah dikerjakan di luar aplikasi.
    """

    harta_preview_changed = Signal(object)
    worksheet_workbook_imported = Signal(object)

    VALIDATION_COLUMN_WIDTHS = {
        0: 165,
        1: 300,
        2: 90,
        3: 70,
        4: 300,
    }

    PREVIEW_COLUMN_WIDTHS = {
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
        self.worksheet_workbook_importer = WorksheetWorkbookImporter()
        self._install_worksheet_import_action()
        self._optimize_interactive_ui()

    def _install_worksheet_import_action(self):
        self.import_worksheet_button = QPushButton("📘 Impor Kertas Kerja yang Sudah Terisi")
        self.import_worksheet_button.setObjectName("secondaryButton")
        self.import_worksheet_button.setMinimumHeight(38)
        self.import_worksheet_button.setToolTip(
            "Impor workbook kertas kerja kantor (sheet tahun + SIMULASI I) agar pekerjaan yang sudah dilakukan di Excel tidak perlu diinput ulang."
        )
        self.import_worksheet_button.clicked.connect(self.choose_worksheet_workbook)

        self.import_bupot_checkbox = QCheckBox("Impor Bupot dari sheet tahun secara otomatis")
        self.import_bupot_checkbox.setChecked(True)
        self.import_bupot_checkbox.setToolTip(
            "Jika aktif, seluruh Bupot yang terbaca pada sheet tahun (mis. 2025) ikut masuk ke tab Penghasilan & PPh."
        )

        parent = self.validate_button.parentWidget()
        if parent is not None and parent.layout() is not None:
            parent.layout().addWidget(self.import_bupot_checkbox)
            parent.layout().addWidget(self.import_worksheet_button)

    def choose_worksheet_workbook(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Kertas Kerja yang Sudah Terisi",
            "",
            "Kertas Kerja Excel (*.xlsx *.xls);;Semua File (*.*)",
        )
        if not file_path:
            return

        include_bupot = self.import_bupot_checkbox.isChecked()
        self.status_label.setText("Membaca kertas kerja yang sudah terisi...")
        self.progress.setVisible(True)
        self.progress.setValue(25)
        try:
            result = self.worksheet_workbook_importer.parse(Path(file_path))
        except Exception as exc:
            self.progress.setVisible(False)
            self.status_label.setText(f"Gagal membaca kertas kerja: {exc}")
            QMessageBox.critical(self, "Import Kertas Kerja Gagal", str(exc))
            return

        if result.errors:
            self.progress.setVisible(False)
            self.status_label.setText("Kertas kerja tidak dapat diimpor karena struktur/identitas belum valid.")
            QMessageBox.warning(
                self,
                "Kertas Kerja Belum Valid",
                "\n".join(f"• {issue.message}" for issue in result.errors),
            )
            return

        try:
            exists = self.worksheet_workbook_importer.has_existing_state(result)
        except Exception:
            exists = False

        if exists:
            bupot_note = (
                "Bupot dari workbook juga akan mengganti Bupot tersimpan. "
                if include_bupot
                else "Bupot tersimpan dipertahankan dan tidak diganti. "
            )
            answer = QMessageBox.question(
                self,
                "Worksheet Sudah Ada",
                f"Worksheet NPWP {result.npwp} Tahun {result.tahun_pajak} sudah memiliki data tersimpan.\n\n"
                "Impor kertas kerja ini akan mengganti state Penghasilan/PPh untuk WP dan tahun tersebut. "
                f"{bupot_note}"
                "Harta menggunakan isi SIMULASI I sebagai baseline import.\n\nLanjutkan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self.progress.setVisible(False)
                self.status_label.setText("Impor kertas kerja dibatalkan.")
                return

        self.progress.setValue(70)
        try:
            self.worksheet_workbook_importer.persist(
                result,
                include_bupot=include_bupot,
            )
        except Exception as exc:
            self.progress.setVisible(False)
            self.status_label.setText(f"Gagal menyimpan hasil import kertas kerja: {exc}")
            QMessageBox.critical(self, "Penyimpanan Gagal", str(exc))
            return

        self.progress.setValue(100)
        warning_text = ""
        if result.warnings:
            warning_text = "\n\nCatatan:\n" + "\n".join(
                f"• {issue.message}" for issue in result.warnings
            )

        imported_bupot_count = len(result.bupot_rows) if include_bupot else 0
        bupot_summary = (
            f"{imported_bupot_count} Bupot diimpor otomatis"
            if include_bupot
            else "Bupot tidak diimpor"
        )
        self.status_label.setText(
            f"Kertas kerja berhasil diimpor: {result.nama_wp or 'WP'} • Tahun {result.tahun_pajak} • "
            f"{bupot_summary} • {len(result.harta_rows)} Harta."
        )
        QMessageBox.information(
            self,
            "Import Kertas Kerja Berhasil",
            f"Data kertas kerja berhasil masuk ke Worksheet aplikasi.\n\n"
            f"Nama: {result.nama_wp or '-'}\nNPWP: {result.npwp}\nTahun: {result.tahun_pajak}\n"
            f"Bupot terbaca: {len(result.bupot_rows)} baris\n"
            f"Bupot diimpor: {'YA' if include_bupot else 'TIDAK'}\n"
            f"Harta: {len(result.harta_rows)} baris"
            f"{warning_text}",
        )
        self.worksheet_workbook_imported.emit(result)

    def _optimize_interactive_ui(self):
        """Optimasi seluruh area scroll/tabel yang sering berinteraksi dengan user."""
        optimize_scroll_area(self.scroll_area, vertical_step=26)

        optimize_table_interaction(
            self.table,
            column_widths=self.VALIDATION_COLUMN_WIDTHS,
            row_height=36,
            horizontal_step=18,
            vertical_step=18,
            stretch_column=4,
        )

        optimize_table_interaction(
            self.worksheet_table,
            column_widths=self.PREVIEW_COLUMN_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )

    @staticmethod
    def _set_info_emphasis(label, active: bool) -> None:
        font = label.font()
        font.setBold(bool(active))
        label.setFont(font)

    def set_files(self, files):
        super().set_files(files)
        self.harta_preview_changed.emit(None)

    def clear_selection(self):
        super().clear_selection()
        self.harta_preview_changed.emit(None)

    def validate_all(self):
        self.harta_preview_changed.emit(None)
        super().validate_all()

        result = self.last_result
        if result is None:
            return

        if result.total_rows == 0:
            self.preview_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.status_label.setText(
                f"Validasi selesai: {result.found_count}/6 kategori ditemukan, "
                "tetapi semua file yang terbaca NIHIL/template (0 baris data harta)."
            )
            self.worksheet_info.setText("Tidak ada data harta untuk dipreview")
            self._set_info_emphasis(self.worksheet_info, False)

    def build_worksheet_preview(self):
        result = self.last_result
        if result is not None and result.total_rows == 0:
            self.export_button.setEnabled(False)
            self.worksheet_info.setText("Tidak ada data harta untuk dipreview")
            self.status_label.setText(
                "Preview tidak dibuat karena file yang dipilih tidak memiliki baris data harta."
            )
            self.harta_preview_changed.emit(None)
            QMessageBox.information(
                self,
                "Data Harta Kosong",
                "File yang dipilih terdeteksi sebagai NIHIL/template dan memiliki 0 baris data.\n\n"
                "Gunakan file hasil ekspor Coretax yang sudah berisi data harta untuk membuat preview SIMULASI I.",
            )
            return

        super().build_worksheet_preview()

        pipeline_result = self.last_pipeline_result
        if (
            pipeline_result is not None
            and not pipeline_result.errors
            and pipeline_result.worksheet_rows
        ):
            self.harta_preview_changed.emit(pipeline_result)
        else:
            self.harta_preview_changed.emit(None)

    def _render_result(self, result):
        with suspended_updates(self.table):
            super()._render_result(result)
        self._set_info_emphasis(self.preview_info, self.table.rowCount() > 0)

    def _render_worksheet_preview(self, result):
        with suspended_updates(self.worksheet_table):
            super()._render_worksheet_preview(result)
        self._set_info_emphasis(
            self.worksheet_info,
            self.worksheet_table.rowCount() > 0,
        )

    def _reset_result_ui(self):
        with suspended_updates(self.table):
            super()._reset_result_ui()
        self._set_info_emphasis(self.preview_info, False)

    def _reset_worksheet_preview(self):
        with suspended_updates(self.worksheet_table):
            super()._reset_worksheet_preview()
        self._set_info_emphasis(self.worksheet_info, False)
