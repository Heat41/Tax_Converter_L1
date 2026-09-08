from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ui.pages.worksheet_page_view import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Tambahkan identitas WP pada tab Riwayat Audit.

    Identitas utama memakai Nama WP dari pipeline bila tersedia. Jika file
    produksi tidak menyediakan kolom Nama Wajib Pajak, fallback hanya memakai
    ATAS NAMA ketika seluruh Original Import memiliki satu nama yang konsisten.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._install_audit_identity()
        self._update_audit_identity()

    def _install_audit_identity(self):
        self.audit_identity_panel = QWidget()
        grid = QGridLayout(self.audit_identity_panel)
        grid.setContentsMargins(0, 8, 0, 8)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        labels = (
            ("Nama WP", "audit_wp_name_value"),
            ("NPWP", "audit_npwp_value"),
            ("Tahun Pajak", "audit_year_value"),
        )
        for row_index, (caption, attribute) in enumerate(labels):
            key_label = QLabel(caption)
            key_label.setObjectName("mutedLabel")
            key_label.setMinimumWidth(95)

            value_label = QLabel("-")
            value_label.setStyleSheet("color:#102A43; font-weight:700;")
            value_label.setTextInteractionFlags(value_label.textInteractionFlags())
            setattr(self, attribute, value_label)

            grid.addWidget(key_label, row_index, 0)
            grid.addWidget(value_label, row_index, 1)

        grid.setColumnStretch(1, 1)

        info_card = self.audit_summary.parentWidget()
        if info_card is not None and info_card.layout() is not None:
            # title = 0, description = 1, identity = 2, summary = 3
            info_card.layout().insertWidget(2, self.audit_identity_panel)

    def _resolve_audit_wp_name(self) -> str:
        result = self.harta_pipeline_result
        explicit_name = getattr(result, "nama_wp", None) if result is not None else None
        if explicit_name:
            return " ".join(str(explicit_name).strip().split())

        unique = {}
        for row in self.harta_original_rows:
            name = " ".join(str(getattr(row, "atas_nama", "") or "").strip().split())
            if name:
                unique.setdefault(name.casefold(), name)
        if len(unique) == 1:
            return next(iter(unique.values()))
        return "Belum terdeteksi"

    def _update_audit_identity(self):
        if not hasattr(self, "audit_wp_name_value"):
            return

        result = self.harta_pipeline_result
        if result is None:
            self.audit_wp_name_value.setText("-")
            self.audit_npwp_value.setText("-")
            self.audit_year_value.setText("-")
            return

        nama_wp = self._resolve_audit_wp_name()
        npwp = self.harta_npwp or getattr(result, "npwp", None) or "Belum terdeteksi"
        year = getattr(result, "current_year", None) or "Belum terdeteksi"

        self.audit_wp_name_value.setText(str(nama_wp))
        self.audit_npwp_value.setText(str(npwp))
        self.audit_year_value.setText(str(year))

    def load_harta_preview(self, pipeline_result):
        super().load_harta_preview(pipeline_result)
        self._update_audit_identity()

    def clear_harta_preview(self):
        super().clear_harta_preview()
        self._update_audit_identity()
