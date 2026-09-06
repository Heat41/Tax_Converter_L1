from ui.pages.import_coretax_page import ImportCoretaxPage as BaseImportCoretaxPage


class ImportCoretaxPage(BaseImportCoretaxPage):
    """Presentation wrapper untuk state label pada halaman Impor Coretax.

    Info tabel tetap regular saat kosong, lalu otomatis bold ketika tabel
    sudah memiliki hasil agar state terisi lebih mudah dibedakan secara visual.
    """

    @staticmethod
    def _set_info_emphasis(label, active: bool) -> None:
        font = label.font()
        font.setBold(bool(active))
        label.setFont(font)

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
