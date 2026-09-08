from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from ui.pages.worksheet_pph_stage2 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_scroll_area


class WorksheetPage(BaseWorksheetPage):
    """Perbaikan layout PPh untuk mode windowed.

    Ada dua level scrolling yang sengaja dipisahkan:
    - tabel Bupot menangani scroll horizontal untuk kolom yang lebar;
    - halaman PPh memakai QScrollArea vertikal agar card/bagian di bawah tetap
      dapat diakses saat tinggi aplikasi mengecil.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._install_windowed_bupot_scrolling()
        self._install_windowed_pph_page_scrolling()

    def _install_windowed_bupot_scrolling(self):
        table = self.bupot_table

        # Abaikan sizeHint berbasis total lebar kolom agar tabel dapat menyusut
        # mengikuti area konten saat aplikasi tidak dimaksimalkan.
        table.setMinimumWidth(0)
        table.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)

        # Horizontal scroll milik tabel digunakan untuk mencapai PENGURANG/NETTO.
        # Vertical tabel tetap tersedia bila jumlah baris Bupot memang banyak.
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        bupot_card = table.parentWidget()
        if bupot_card is not None:
            bupot_card.setMinimumWidth(0)
            bupot_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pph_tab.setMinimumWidth(0)
        self.pph_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _install_windowed_pph_page_scrolling(self):
        """Bungkus seluruh konten PPh dengan scroll vertikal level halaman."""
        tab_index = self.tabs.indexOf(self.pph_tab)
        if tab_index < 0:
            return

        tab_text = self.tabs.tabText(tab_index)
        tab_icon = self.tabs.tabIcon(tab_index)
        tab_tooltip = self.tabs.tabToolTip(tab_index)

        self.tabs.removeTab(tab_index)

        self.pph_scroll_area = QScrollArea()
        self.pph_scroll_area.setObjectName("pphPageScrollArea")
        self.pph_scroll_area.setWidgetResizable(True)
        self.pph_scroll_area.setFrameShape(QFrame.NoFrame)
        self.pph_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pph_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.pph_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.pph_scroll_area.setMinimumWidth(0)
        self.pph_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Konten perlu tinggi minimum agar area scroll memiliki range nyata pada
        # windowed mode. Lebar tetap mengikuti viewport.
        self.pph_tab.setMinimumHeight(650)
        self.pph_scroll_area.setWidget(self.pph_tab)
        optimize_scroll_area(self.pph_scroll_area, vertical_step=24)

        self.tabs.insertTab(tab_index, self.pph_scroll_area, tab_icon, tab_text)
        self.tabs.setTabToolTip(tab_index, tab_tooltip)
