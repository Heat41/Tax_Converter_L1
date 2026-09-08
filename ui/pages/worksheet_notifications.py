from ui.notifications import ToastNotification
from ui.pages.worksheet_audit_identity import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Tambahkan toast notification pada aksi penting Worksheet.

    Banner inline tetap dipertahankan sebagai status permanen, sedangkan toast
    hanya memberi feedback singkat tanpa memblokir pekerjaan user.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toast_notification = ToastNotification(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast_notification"):
            self.toast_notification._reposition()

    def load_harta_preview(self, pipeline_result):
        super().load_harta_preview(pipeline_result)
        if pipeline_result is None or not getattr(pipeline_result, "worksheet_rows", None):
            return

        if self.last_harta_save_error:
            self.toast_notification.show_message(
                "Data Harta terbaca, tetapi draft database gagal dipulihkan.",
                "warning",
            )
        elif self.harta_restored_from_db:
            self.toast_notification.show_message(
                "Draft Worksheet Harta berhasil dipulihkan dari database.",
                "success",
            )
        else:
            self.toast_notification.show_message(
                "Preview Harta berhasil tersambung ke Worksheet.",
                "info",
            )

    def save_harta_changes(self):
        had_unsaved = self._has_unsaved_harta_changes()
        result = super().save_harta_changes()
        if not had_unsaved:
            return result

        if self.last_harta_save_error:
            self.toast_notification.show_message(
                "Perubahan belum tersimpan ke database.",
                "error",
                3600,
            )
        elif result is not None and getattr(result, "persisted", False):
            self.toast_notification.show_message(
                f"Perubahan tersimpan ke database • {result.audit_count} audit baru.",
                "success",
            )
        else:
            self.toast_notification.show_message(
                "Perubahan tersimpan pada sesi Worksheet.",
                "info",
            )
        return result

    def reset_harta_to_import(self):
        had_changes = self._has_any_harta_changes()
        super().reset_harta_to_import()
        if had_changes:
            self.toast_notification.show_message(
                "Edited / Current dikembalikan ke Original Import. Simpan untuk memperbarui database.",
                "warning",
                3600,
            )
