from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QTableWidgetItem,
)

from ui.pages.worksheet_pph_stage7 import WorksheetPage as BaseWorksheetPage
from ui.performance import optimize_scroll_area


class WorksheetPage(BaseWorksheetPage):
    """Perbaikan Stage 7 berdasarkan hasil uji nyata worksheet EVY BACHTIAR.

    Perbaikan:
    - field Penghasilan Dalam Negeri Lainnya dan Zakat pada Ringkasan PPh selalu
      mengikuti state yang benar-benar dipakai engine kalkulasi;
    - Total Harta Tahun Sebelumnya dapat diisi sebagai baseline manual bila file
      Coretax tahun berjalan tidak membawa nilai tahun sebelumnya;
    - rekonsiliasi memberi informasi sumber baseline agar nilai 0 yang sebenarnya
      berarti 'belum tersedia' tidak dianggap sebagai baseline valid;
    - hasil impor workbook Stage 8B.1 langsung mengisi tabel Bupot dari hasil
      parsing workbook, sehingga UI tidak bergantung pada siklus reload database;
    - tabel Harta / SIMULASI I menyediakan viewport minimal 10 baris data;
    - halaman Harta / SIMULASI I memiliki vertical page scrolling seperti halaman
      Penghasilan dan Analisis, sehingga toolbar dan tabel tetap dapat diakses pada
      tinggi window yang terbatas.
    """

    HARTA_VISIBLE_ROWS = 10
    HARTA_ROW_HEIGHT = 34

    @staticmethod
    def _default_reconciliation_manual():
        state = BaseWorksheetPage._default_reconciliation_manual()
        state["harta_sebelumnya_override"] = 0.0
        return state

    def __init__(self, parent=None):
        super().__init__(parent)

        # Baseline tahun sebelumnya tidak selalu tersedia di file Coretax 2025.
        # Field ini tetap menampilkan nilai otomatis bila ada, tetapi user boleh
        # memberikan override manual. Masukkan 0 untuk kembali ke nilai otomatis.
        self.harta_prev_value.setReadOnly(False)
        self.harta_prev_value.setObjectName("")
        self.harta_prev_value.setToolTip(
            "Isi Total Harta Tahun Sebelumnya bila baseline tidak tersedia dari file Coretax. "
            "Masukkan 0 untuk menggunakan nilai otomatis."
        )
        self.harta_prev_value.editingFinished.connect(
            self._on_harta_previous_baseline_finished
        )
        self._repolish_widget(self.harta_prev_value)
        self._configure_harta_visible_rows()
        self._install_harta_page_scrolling()
        self._render_reconciliation()
        self._recalculate_pph_summary()

    def _configure_harta_visible_rows(self):
        """Pastikan tabel Harta menampilkan sekitar 10 baris tanpa mengecilkan row height."""
        header = self.harta_table.horizontalHeader()
        header_height = max(header.height(), header.sizeHint().height())
        scrollbar_height = self.harta_table.horizontalScrollBar().sizeHint().height()
        frame = self.harta_table.frameWidth() * 2
        padding = 8
        target_height = (
            header_height
            + (self.HARTA_VISIBLE_ROWS * self.HARTA_ROW_HEIGHT)
            + scrollbar_height
            + frame
            + padding
        )
        self.harta_table.setMinimumHeight(target_height)

    def _install_harta_page_scrolling(self):
        """Bungkus seluruh isi tab Harta dengan scroll vertikal level halaman.

        Tabel tetap mempunyai scroll horizontal sendiri untuk kolom yang lebar.
        Scroll vertikal ini khusus untuk bergerak dari info/header ke toolbar dan
        area tabel ketika tinggi jendela tidak cukup menampilkan semuanya sekaligus.
        """
        tab_index = self.tabs.indexOf(self.harta_tab)
        if tab_index < 0:
            return

        tab_text = self.tabs.tabText(tab_index)
        tab_icon = self.tabs.tabIcon(tab_index)
        tab_tooltip = self.tabs.tabToolTip(tab_index)

        self.tabs.removeTab(tab_index)

        self.harta_scroll_area = QScrollArea()
        self.harta_scroll_area.setObjectName("hartaPageScrollArea")
        self.harta_scroll_area.setWidgetResizable(True)
        self.harta_scroll_area.setFrameShape(QFrame.NoFrame)
        self.harta_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.harta_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.harta_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.harta_scroll_area.setMinimumWidth(0)
        self.harta_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Tinggi minimum konten memaksa QScrollArea menyediakan range vertikal saat
        # aplikasi berada pada mode windowed. Lebar tetap mengikuti viewport.
        self.harta_tab.setMinimumWidth(0)
        self.harta_tab.setMinimumHeight(720)
        self.harta_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.harta_scroll_area.setWidget(self.harta_tab)
        optimize_scroll_area(self.harta_scroll_area, vertical_step=24)

        self.tabs.insertTab(tab_index, self.harta_scroll_area, tab_icon, tab_text)
        self.tabs.setTabToolTip(tab_index, tab_tooltip)

    def load_workbook_import_result(self, import_result):
        """Muat hasil Stage 8B.1 langsung ke seluruh Worksheet.

        Persistence tetap dilakukan oleh WorksheetWorkbookImporter. Method ini
        khusus menyinkronkan state UI setelah import. Bupot memakai baris hasil
        parser secara langsung agar data yang baru diimpor langsung terlihat.
        """
        pipeline = getattr(import_result, "pipeline_result", None)
        if pipeline is not None:
            self.load_harta_preview(pipeline)

        rows = list(getattr(import_result, "bupot_rows", None) or [])
        if hasattr(self, "_render_bupot_rows"):
            self._render_bupot_rows(rows)
            self._bupot_saved_rows = list(rows)
            self._bupot_restored_from_db = bool(rows)
            self._bupot_last_save_error = None
            self._validate_and_refresh_bupot()

        # Komponen PPh/penghasilan sudah dipersist sebelum signal diterima.
        # Muat ulang sekali setelah identitas Harta tersambung agar seluruh card
        # turunan (PTKP, UMKM, penghasilan lainnya, analisis) memakai state yang sama.
        if pipeline is not None and hasattr(self, "_load_pph_state_for_current_wp"):
            self._load_pph_state_for_current_wp()
            # _load_pph_state_for_current_wp membaca database; render ulang hasil
            # parser setelahnya agar Bupot workbook menjadi sumber tampilan langsung.
            if rows:
                self._render_bupot_rows(rows)
                self._bupot_saved_rows = list(rows)
                self._bupot_restored_from_db = True
                self._validate_and_refresh_bupot()

        if hasattr(self, "toast_notification"):
            if rows:
                self.toast_notification.show_message(
                    f"{len(rows)} baris Bupot dari kertas kerja dimuat otomatis.",
                    "success",
                    3200,
                )
            else:
                self.toast_notification.show_message(
                    "Kertas kerja berhasil dimuat, tetapi tidak ada baris Bupot yang terbaca.",
                    "warning",
                    4200,
                )

    @staticmethod
    def _repolish_widget(widget):
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _automatic_harta_totals(self):
        rows = self.harta_current_rows or self.harta_original_rows
        previous = sum(float(row.nilai_tahun_sebelumnya or 0) for row in rows)
        current = sum(float(row.nilai_tahun_berjalan or 0) for row in rows)
        return previous, current

    def _harta_totals_for_reconciliation(self):
        automatic_previous, current = self._automatic_harta_totals()
        override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )
        previous = override if override > 0 else automatic_previous
        return previous, current

    def _on_harta_previous_baseline_finished(self):
        if self._rendering_reconciliation:
            return

        automatic_previous, _ = self._automatic_harta_totals()
        previous_override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )
        try:
            value = self._parse_bupot_money(self.harta_prev_value.text())
            if value < 0:
                raise ValueError("negative")
        except ValueError:
            value = previous_override
            self.toast_notification.show_message(
                "Total Harta Tahun Sebelumnya tidak valid. Gunakan angka positif.",
                "warning",
                3600,
            )

        # Jika user mengetik nilai yang sama dengan sumber otomatis, tidak perlu
        # menyimpan override. Nilai 0 juga berarti kembali ke sumber otomatis.
        if value <= 0 or (
            automatic_previous > 0 and abs(value - automatic_previous) < 0.5
        ):
            value = 0.0

        self._reconciliation_manual["harta_sebelumnya_override"] = float(value)
        self._render_reconciliation()
        self._refresh_bupot_actions()

    def _recalculate_pph_summary(self):
        super()._recalculate_pph_summary()

        # Stage 6 mengubah dua komponen ini menjadi read-only karena nilainya
        # berasal dari card Penghasilan Lainnya. Pastikan teks ringkasan juga
        # mengikuti state internal setiap kali kalkulasi dilakukan.
        if not hasattr(self, "pph_auto_values"):
            return
        for key in (
            "penghasilan_neto_lainnya",
            "pengurang_penghasilan_neto",
        ):
            field = self.pph_auto_values.get(key)
            if field is not None:
                field.setText(
                    self._format_bupot_money(
                        self._pph_component_values.get(key, 0.0)
                    )
                )

    def _render_reconciliation(self):
        super()._render_reconciliation()
        if not hasattr(self, "reconciliation_status"):
            return

        automatic_previous, _ = self._automatic_harta_totals()
        override = float(
            self._reconciliation_manual.get("harta_sebelumnya_override", 0.0) or 0
        )

        # Super menampilkan effective previous. Pastikan field baseline tetap
        # editable setelah render dan jelaskan sumber nilai yang sedang digunakan.
        self.harta_prev_value.setReadOnly(False)
        self.harta_prev_value.setObjectName("")
        self._repolish_widget(self.harta_prev_value)

        base_status = self.reconciliation_status.text()
        if override > 0:
            source = "Baseline Harta tahun sebelumnya: MANUAL"
        elif automatic_previous > 0:
            source = "Baseline Harta tahun sebelumnya: OTOMATIS"
        else:
            source = (
                "⚠ Baseline Harta tahun sebelumnya belum tersedia. "
                "Isi Total Harta Tahun Sebelumnya sebelum menilai hasil rekonsiliasi"
            )
        self.reconciliation_status.setText(f"{source} • {base_status}")
