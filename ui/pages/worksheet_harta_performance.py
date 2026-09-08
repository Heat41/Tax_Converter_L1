from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView

from ui.pages.worksheet_page import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Optimasi rendering tabel Worksheet Harta untuk mode windowed.

    ResizeToContents pada banyak kolom dapat memaksa Qt mengukur ulang isi tabel
    ketika viewport berubah atau scrollbar bergerak. Lapisan ini menggantinya
    dengan ukuran kolom stabil dan scroll per-pixel agar interaksi lebih halus.
    """

    HARTA_COLUMN_WIDTHS = {
        0: 55,   # NO
        1: 95,   # KODE EFORM
        2: 85,   # KODE CT
        3: 230,  # NAMA HARTA
        4: 235,  # NOMOR AKUN / KETERANGAN
        5: 155,  # ATAS NAMA
        6: 145,  # NAMA BANK
        7: 105,  # TH PEROLEHAN
        8: 135,  # TAHUN SEBELUMNYA
        9: 135,  # TAHUN BERJALAN
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._optimize_harta_table()

    def _optimize_harta_table(self):
        table = self.harta_table
        header = table.horizontalHeader()
        vertical = table.verticalHeader()

        # Hindari kalkulasi ResizeToContents berulang saat window di-resize.
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)

        for column, width in self.HARTA_COLUMN_WIDTHS.items():
            table.setColumnWidth(column, width)

        # Tinggi baris stabil mengurangi geometry recalculation saat scroll.
        vertical.setSectionResizeMode(QHeaderView.Fixed)
        vertical.setDefaultSectionSize(34)
        vertical.setMinimumSectionSize(34)

        # Scroll per-pixel terasa lebih halus dibanding perpindahan per-item.
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.horizontalScrollBar().setSingleStep(18)
        table.verticalScrollBar().setSingleStep(18)

        # Hindari layout teks multi-line yang tidak diperlukan pada grid Harta.
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)

        # Selection/editing tetap sama, hanya viewport yang dioptimalkan.
        table.setAutoScroll(True)
        table.setCornerButtonEnabled(False)
