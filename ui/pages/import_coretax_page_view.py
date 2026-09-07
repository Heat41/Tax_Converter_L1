from PySide6.QtWidgets import QMessageBox

from ui.pages.import_coretax_page import ImportCoretaxPage as BaseImportCoretaxPage


class ImportCoretaxPage(BaseImportCoretaxPage):
    """Presentation wrapper untuk state halaman Impor Coretax."""

    @staticmethod
    def _set_info_emphasis(label, active: bool) -> None:
        font = label.font()
        font.setBold(bool(active))
        label.setFont(font)

    def validate_all(self):
        super().validate_all()

        result = self.last_result
        if result is None:
            return

        # File template/NIHIL boleh lolos validasi struktur, tetapi tidak punya
        # baris harta untuk dibentuk menjadi preview SIMULASI I.
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
            QMessageBox.information(
                self,
                "Data Harta Kosong",
                "File yang dipilih terdeteksi sebagai NIHIL/template dan memiliki 0 baris data.\n\n"
                "Gunakan file hasil ekspor Coretax yang sudah berisi data harta untuk membuat preview SIMULASI I.",
            )
            return

        super().build_worksheet_preview()

    def _render_result(self, result):
        super()._render_result(result)
        self._set_info_emphasis(self.preview_info, self.table.rowCount() > 0)

    def _render_worksheet_preview(self, result):
        super()._render_worksheet_preview(result)
        self._set_info_emphasis(
            self.worksheet_info,
            self.worksheet_table.rowCount() > 0,
        )

    def _reset_result_ui(self):
        super()._reset_result_ui()
        self._set_info_emphasis(self.preview_info, False)

    def _reset_worksheet_preview(self):
        super()._reset_worksheet_preview()
        self._set_info_emphasis(self.worksheet_info, False)
