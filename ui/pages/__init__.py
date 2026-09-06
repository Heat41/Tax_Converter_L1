"""UI pages package.

Compatibility hook for ImportCoretaxPage file selection.
The page historically replaced its selection every time the file dialog was
opened. Until the method is folded directly into the page class, patch it here
so repeated selections append to the current six-file batch safely.
"""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from . import import_coretax_page as _import_coretax_page


def _choose_files_append(self):
    files, _ = QFileDialog.getOpenFileNames(
        self,
        "Pilih File Coretax (maksimal 6)",
        "",
        "File Excel / CSV (*.xlsx *.xls *.csv);;Semua File (*.*)",
    )
    if not files:
        return

    new_files = [Path(path).resolve() for path in files]
    combined = list(dict.fromkeys([*self.selected_files, *new_files]))

    if len(combined) > 6:
        QMessageBox.warning(
            self,
            "Batas File",
            "Maksimal 6 file dapat dipilih. File yang sudah dipilih tetap dipertahankan.",
        )
        return

    self.set_files(combined)
    self.status_label.setText(
        f"{len(self.selected_files)} file dipilih. Silakan tambah file lain atau mulai validasi."
    )


_import_coretax_page.ImportCoretaxPage.choose_files = _choose_files_append

ImportCoretaxPage = _import_coretax_page.ImportCoretaxPage

__all__ = ["ImportCoretaxPage"]
