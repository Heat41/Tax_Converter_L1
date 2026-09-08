from contextlib import contextmanager
from typing import Mapping, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView


def optimize_table_interaction(
    table,
    *,
    column_widths: Optional[Mapping[int, int]] = None,
    row_height: int = 34,
    horizontal_step: int = 18,
    vertical_step: int = 18,
    stretch_column: Optional[int] = None,
    minimum_section_size: int = 48,
) -> None:
    """Konfigurasi tabel interaktif agar scroll/resize lebih ringan.

    Prinsip utama:
    - hindari ResizeToContents pada grid yang sering di-scroll/resize;
    - gunakan geometri baris/kolom yang stabil;
    - gunakan ScrollPerPixel;
    - matikan word-wrap pada grid data.
    """
    header = table.horizontalHeader()
    vertical = table.verticalHeader()

    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(minimum_section_size)

    for column, width in (column_widths or {}).items():
        table.setColumnWidth(column, width)

    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.Stretch)

    vertical.setSectionResizeMode(QHeaderView.Fixed)
    vertical.setDefaultSectionSize(row_height)
    vertical.setMinimumSectionSize(row_height)

    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.horizontalScrollBar().setSingleStep(horizontal_step)
    table.verticalScrollBar().setSingleStep(vertical_step)

    table.setWordWrap(False)
    table.setTextElideMode(Qt.ElideRight)
    table.setCornerButtonEnabled(False)


def optimize_scroll_area(scroll_area, *, vertical_step: int = 24) -> None:
    """Buat scroll halaman panjang terasa lebih halus dan konsisten."""
    scroll_area.verticalScrollBar().setSingleStep(vertical_step)


@contextmanager
def suspended_updates(widget):
    """Tunda repaint saat isi tabel sedang diganti secara batch."""
    widget.setUpdatesEnabled(False)
    try:
        yield widget
    finally:
        widget.setUpdatesEnabled(True)
        if hasattr(widget, "viewport"):
            widget.viewport().update()
        else:
            widget.update()
