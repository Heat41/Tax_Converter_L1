from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem

from ui.pages.worksheet_pph_stage7 import WorksheetPage as BaseWorksheetPage


class WorksheetPage(BaseWorksheetPage):
    """Perbaikan Stage 7 berdasarkan hasil uji nyata worksheet EVY BACHTIAR.

    Perbaikan:
    - field Penghasilan Dalam Negeri Lainnya dan Zakat pada Ringkasan PPh selalu
      mengikuti state yang benar-benar dipakai engine kalkulasi;
    - Total Harta Tahun Sebelumnya dapat diisi sebagai baseline manual bila file
      Coretax tahun berjalan tidak membawa nilai tahun sebelumnya;
    - rekonsiliasi memberi informasi sumber baseline agar nilai 0 yang sebenarnya
      berarti 'belum tersedia' tidak dianggap sebagai baseline valid.
    """

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
        self._render_reconciliation()
        self._recalculate_pph_summary()

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
