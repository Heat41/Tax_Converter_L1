from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractScrollArea, QSizePolicy

from ui.pages.worksheet_pph_stage2 import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Perbaikan layout Bupot untuk mode windowed.

    QTableWidget tidak boleh memaksa parent mengikuti total lebar seluruh kolom.
    Biarkan tabel mengecil mengikuti viewport dan gunakan scrollbar horizontal
    untuk mengakses kolom yang berada di sisi kanan.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._install_windowed_bupot_scrolling()

    def _install_windowed_bupot_scrolling(self):
        table = self.bupot_table

        # Abaikan sizeHint berbasis total lebar kolom agar tabel dapat menyusut
        # mengikuti area konten saat aplikasi tidak dimaksimalkan.
        table.setMinimumWidth(0)
        table.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)

        # Scroll horizontal harus tetap dapat ditemukan user pada windowed mode.
        # ScrollPerPixel dari stage sebelumnya tetap dipertahankan.
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Parent card/tab juga tidak boleh menahan minimum width dari isi tabel.
        bupot_card = table.parentWidget()
        if bupot_card is not None:
            bupot_card.setMinimumWidth(0)
            bupot_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pph_tab.setMinimumWidth(0)
        self.pph_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
