from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class WorksheetPage(QWidget):
    """Halaman worksheet utama.

    Tab Harta menerima hasil pipeline SIMULASI I dari halaman Impor Coretax.
    Tab Penghasilan & PPh tetap terpisah dan disiapkan untuk input manual.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.harta_pipeline_result = None
        self.harta_original_rows = []
        self.harta_current_rows = []
        self.harta_mode = "original"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Worksheet")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Periksa hasil Harta L-1 dan lengkapi data penghasilan serta PPh Tahunan."
        )
        subtitle.setObjectName("pageSubTitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("worksheetTabs")
        self.tabs.setDocumentMode(True)

        self.harta_tab = self._build_harta_tab()
        self.pph_tab = self._build_pph_tab()

        self.tabs.addTab(self.harta_tab, "Harta / SIMULASI I")
        self.tabs.addTab(self.pph_tab, "Penghasilan & PPh 2025")

        layout.addWidget(self.tabs, 1)

    def _build_harta_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        heading = QLabel("Worksheet Harta — SIMULASI I")
        heading.setObjectName("sectionTitle")
        description = QLabel(
            "Data Harta pada bagian ini berasal langsung dari preview hasil import Coretax. "
            "Original Import menyimpan hasil awal pipeline; Edited / Current akan menjadi "
            "area koreksi pada tahap editor berikutnya."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)

        self.harta_status = QLabel("Belum ada preview Harta dari halaman Impor Coretax.")
        self.harta_status.setObjectName("mutedLabel")
        self.harta_status.setWordWrap(True)

        info_layout.addWidget(heading)
        info_layout.addWidget(description)
        info_layout.addWidget(self.harta_status)
        layout.addWidget(info_card)

        toolbar = QHBoxLayout()
        self.original_button = QPushButton("Original Import")
        self.original_button.setObjectName("secondaryButton")
        self.current_button = QPushButton("Edited / Current")
        self.current_button.setObjectName("secondaryButton")
        self.save_harta_button = QPushButton("Simpan Perubahan")
        self.save_harta_button.setObjectName("primaryButton")
        self.save_harta_button.setEnabled(False)

        self.original_button.clicked.connect(
            lambda: self._show_harta_mode("original")
        )
        self.current_button.clicked.connect(
            lambda: self._show_harta_mode("current")
        )

        toolbar.addWidget(self.original_button)
        toolbar.addWidget(self.current_button)
        toolbar.addStretch()
        toolbar.addWidget(self.save_harta_button)
        layout.addLayout(toolbar)

        self.harta_table = QTableWidget(0, 10)
        self.harta_table.setHorizontalHeaderLabels([
            "NO",
            "KODE EFORM",
            "KODE CT",
            "NAMA HARTA",
            "NOMOR AKUN / KETERANGAN",
            "ATAS NAMA",
            "NAMA BANK",
            "TH PEROLEHAN",
            "TAHUN SEBELUMNYA",
            "TAHUN BERJALAN",
        ])
        self.harta_table.setAlternatingRowColors(True)
        self.harta_table.verticalHeader().setVisible(False)
        self.harta_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.harta_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.harta_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.harta_table.horizontalHeader().setMinimumSectionSize(80)
        layout.addWidget(self.harta_table, 1)

        return page

    def load_harta_preview(self, pipeline_result):
        """Terima hasil preview dari halaman Impor Coretax."""
        if pipeline_result is None or not getattr(
            pipeline_result, "worksheet_rows", None
        ):
            self.clear_harta_preview()
            return

        self.harta_pipeline_result = pipeline_result
        self.harta_original_rows = list(pipeline_result.worksheet_rows)
        # Untuk saat ini Current dimulai identik dengan Original. Pada tahap
        # editor berikutnya daftar ini akan menjadi state koreksi tersendiri.
        self.harta_current_rows = list(pipeline_result.worksheet_rows)
        self.harta_mode = "original"

        year = pipeline_result.current_year or "-"
        skipped = getattr(pipeline_result.mapping, "skipped_rows", 0)
        self.harta_status.setText(
            f"{len(self.harta_original_rows)} baris Harta tersambung • "
            f"Tahun {year} • {skipped} baris dilewati"
        )
        self._render_harta_rows(self.harta_original_rows)

    def clear_harta_preview(self):
        self.harta_pipeline_result = None
        self.harta_original_rows = []
        self.harta_current_rows = []
        self.harta_mode = "original"
        self.harta_table.clearContents()
        self.harta_table.setRowCount(0)
        self.harta_status.setText(
            "Belum ada preview Harta dari halaman Impor Coretax."
        )
        self.save_harta_button.setEnabled(False)

    def _show_harta_mode(self, mode: str):
        if mode not in {"original", "current"}:
            return
        self.harta_mode = mode
        rows = (
            self.harta_original_rows
            if mode == "original"
            else self.harta_current_rows
        )
        self._render_harta_rows(rows)

        if self.harta_pipeline_result is not None:
            label = "Original Import" if mode == "original" else "Edited / Current"
            year = self.harta_pipeline_result.current_year or "-"
            self.harta_status.setText(
                f"Mode {label} • {len(rows)} baris Harta • Tahun {year}"
            )

    def _render_harta_rows(self, rows):
        self.harta_table.clearContents()
        self.harta_table.setRowCount(len(rows))

        for row_index, item in enumerate(rows):
            values = [
                item.nomor,
                item.kode_eform,
                item.kode_ct,
                item.nama_harta,
                item.nomor_akun_keterangan,
                item.atas_nama,
                item.nama_bank,
                item.tahun_perolehan,
                item.nilai_tahun_sebelumnya,
                item.nilai_tahun_berjalan,
            ]
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(
                    self._format_harta_value(
                        value,
                        numeric=column_index in (8, 9),
                    )
                )
                self.harta_table.setItem(
                    row_index,
                    column_index,
                    table_item,
                )

    @staticmethod
    def _format_harta_value(value, *, numeric: bool = False) -> str:
        if value is None:
            return ""
        if numeric:
            try:
                number = float(value)
                if number == 0:
                    return "0"
                return f"{number:,.0f}".replace(",", ".")
            except (TypeError, ValueError):
                pass
        return str(value)

    def _build_pph_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(14)

        info_card = QFrame(objectName="card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        heading = QLabel("Worksheet Penghasilan & PPh 2025")
        heading.setObjectName("sectionTitle")
        description = QLabel(
            "Bagian ini disiapkan untuk input manual Bupot dan komponen penghasilan. "
            "Data Harta L-1 tetap diproses terpisah melalui SIMULASI I."
        )
        description.setObjectName("pageSubTitle")
        description.setWordWrap(True)

        info_layout.addWidget(heading)
        info_layout.addWidget(description)
        layout.addWidget(info_card)

        bupot_card = QFrame(objectName="card")
        bupot_layout = QVBoxLayout(bupot_card)
        bupot_layout.setContentsMargins(20, 18, 20, 18)
        bupot_layout.setSpacing(10)

        header = QHBoxLayout()
        bupot_title = QLabel("Bukti Potong — Input Manual")
        bupot_title.setObjectName("sectionTitle")
        self.add_bupot_button = QPushButton("+ Tambah Baris")
        self.add_bupot_button.setObjectName("secondaryButton")
        self.remove_bupot_button = QPushButton("Hapus Baris")
        self.remove_bupot_button.setObjectName("secondaryButton")
        self.add_bupot_button.clicked.connect(self._add_bupot_row)
        self.remove_bupot_button.clicked.connect(self._remove_bupot_row)

        header.addWidget(bupot_title)
        header.addStretch()
        header.addWidget(self.add_bupot_button)
        header.addWidget(self.remove_bupot_button)
        bupot_layout.addLayout(header)

        self.bupot_table = QTableWidget(0, 7)
        self.bupot_table.setHorizontalHeaderLabels([
            "NO",
            "JENIS",
            "NPWP PEMBERI KERJA",
            "NO BUPOT",
            "BRUTO",
            "PENGURANG",
            "NETTO",
        ])
        self.bupot_table.setAlternatingRowColors(True)
        self.bupot_table.verticalHeader().setVisible(False)
        self.bupot_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bupot_table.setMinimumHeight(220)
        bupot_layout.addWidget(self.bupot_table)
        layout.addWidget(bupot_card)

        summary_card = QFrame(objectName="card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 18, 20, 18)
        summary_layout.setSpacing(6)

        summary_title = QLabel("Ringkasan Perhitungan")
        summary_title.setObjectName("sectionTitle")
        summary_note = QLabel(
            "UMKM, penghasilan lainnya, pengurang penghasilan neto, PTKP, PPh terutang, "
            "angsuran PPh 25, dan kurang/lebih bayar akan ditambahkan setelah struktur Bupot selesai."
        )
        summary_note.setObjectName("pageSubTitle")
        summary_note.setWordWrap(True)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(summary_note)
        layout.addWidget(summary_card)
        layout.addStretch()

        return page

    def _add_bupot_row(self):
        row = self.bupot_table.rowCount()
        self.bupot_table.insertRow(row)
        no_item = QTableWidgetItem(str(row + 1))
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        self.bupot_table.setItem(row, 0, no_item)

        netto_item = QTableWidgetItem("0")
        netto_item.setFlags(netto_item.flags() & ~Qt.ItemIsEditable)
        self.bupot_table.setItem(row, 6, netto_item)

    def _remove_bupot_row(self):
        selected = sorted(
            {index.row() for index in self.bupot_table.selectedIndexes()},
            reverse=True,
        )
        if not selected and self.bupot_table.rowCount() > 0:
            selected = [self.bupot_table.rowCount() - 1]

        for row in selected:
            self.bupot_table.removeRow(row)

        for row in range(self.bupot_table.rowCount()):
            item = self.bupot_table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.bupot_table.setItem(row, 0, item)
            item.setText(str(row + 1))
