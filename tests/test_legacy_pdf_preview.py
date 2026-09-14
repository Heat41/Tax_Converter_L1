import sys
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from pypdf import PdfWriter

from ui.legacy_pdf_preview import LegacyPdfPreviewDialog


app = QApplication.instance() or QApplication(sys.argv)


def _make_pdf(path: Path, pages: int = 2):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def test_legacy_preview_loads_multipage_pdf(tmp_path):
    pdf = tmp_path / "preview.pdf"
    _make_pdf(pdf, pages=2)

    dialog = LegacyPdfPreviewDialog(pdf)
    try:
        assert dialog.page_count == 2
        assert dialog.current_page == 0
        assert dialog.page_label.text() == "Halaman 1 / 2"
        assert dialog.previous_button.isEnabled() is False
        assert dialog.next_button.isEnabled() is True
    finally:
        dialog.close()
        dialog.deleteLater()


def test_legacy_preview_navigation_and_zoom(tmp_path):
    pdf = tmp_path / "preview.pdf"
    _make_pdf(pdf, pages=2)
    before = pdf.read_bytes()

    dialog = LegacyPdfPreviewDialog(pdf)
    try:
        dialog._next_page()
        assert dialog.current_page == 1
        assert dialog.page_label.text() == "Halaman 2 / 2"

        dialog._previous_page()
        assert dialog.current_page == 0

        dialog._zoom_in()
        assert dialog.zoom_factor > 1.0
        dialog._zoom_reset()
        assert dialog.zoom_factor == 1.0

        assert pdf.read_bytes() == before
    finally:
        dialog.close()
        dialog.deleteLater()


def test_legacy_preview_keyboard_shortcuts(tmp_path):
    pdf = tmp_path / "preview.pdf"
    _make_pdf(pdf, pages=3)

    dialog = LegacyPdfPreviewDialog(pdf)
    try:
        dialog.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Right,
                Qt.KeyboardModifier.NoModifier,
            )
        )
        assert dialog.current_page == 1

        dialog.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Plus,
                Qt.KeyboardModifier.NoModifier,
            )
        )
        assert dialog.zoom_factor > 1.0

        dialog.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_0,
                Qt.KeyboardModifier.NoModifier,
            )
        )
        assert dialog.zoom_factor == 1.0
        assert "Preview sementara" in dialog.file_label.text()
    finally:
        dialog.close()
        dialog.deleteLater()
