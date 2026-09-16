from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.finalization import FinalizationService, ValidationSeverity
from core.finalization_adapter import FinalizationAdapter
from core.export_audit import ExportAuditRecord, ExportAuditService
from core.legacy_1770_static_pdf import Legacy1770StaticPdfService
from core.physical_reconciliation import PhysicalSourceExportReconciler
from core.reverse_coretax_mapping import ReverseCoretaxMappingService
from core.reverse_coretax_official_package import OfficialCoretaxPackageExporter
from core.reverse_coretax_official_package_validator import OfficialCoretaxPackageValidator
from ui.coretax_package_preview import CoretaxPackagePreviewDialog
from ui.legacy_pdf_preview import LegacyPdfPreviewDialog
from ui.notifications import ToastNotification
from ui.performance import optimize_scroll_area, optimize_table_interaction, suspended_updates


class FinalizationPage(QWidget):
    """Stage 8A.2 — pemeriksaan akhir, snapshot FINAL, VOID, dan riwayat."""

    VALIDATION_WIDTHS = {0: 110, 1: 110, 2: 330, 3: 330}
    HISTORY_WIDTHS = {0: 95, 1: 105, 2: 190, 3: 190, 4: 180}

    def __init__(
        self,
        worksheet_source=None,
        parent=None,
        db_path: Optional[Path | str] = None,
    ):
        super().__init__(parent)
        self.worksheet_source = worksheet_source
        self.service = FinalizationService(db_path=db_path)
        self.audit_service = ExportAuditService(db_path=db_path)
        self.current_input = None
        self.current_validation = None
        self.active_snapshot = None
        self._preview_rendering = False
        self._preview_dirty = False
        self._preview_harta_rows = []
        self._preview_bupot_rows = []
        self._preview_identity = None
        self._original_bupot_rows = []

        self._build_ui()
        self.toast_notification = ToastNotification(self)
        self.refresh_page()

    def set_worksheet_source(self, source):
        self.worksheet_source = source
        self.refresh_page()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        title = QLabel("Finalisasi")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Periksa kesiapan Worksheet sebelum membuat snapshot final yang akan menjadi sumber proses export."
        )
        subtitle.setObjectName("pageSubTitle")
        subtitle.setWordWrap(True)
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 8, 8)
        content_layout.setSpacing(14)

        self._build_identity_card(content_layout)
        self._build_summary_card(content_layout)
        self._build_editable_preview_card(content_layout)
        self._build_validation_card(content_layout)
        self._build_actions_card(content_layout)
        self._build_history_card(content_layout)
        self._build_export_history_card(content_layout)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("finalizationScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(content)
        optimize_scroll_area(scroll, vertical_step=24)
        root_layout.addWidget(scroll, 1)

    def _build_identity_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("Identitas Wajib Pajak")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)
        self.identity_labels = {}
        fields = (
            ("Nama Wajib Pajak", "nama_wp"),
            ("NPWP", "npwp"),
            ("Tahun Pajak", "tahun_pajak"),
            ("Status Worksheet", "status"),
            ("Revision Aktif", "revision"),
            ("Tanggal Finalisasi", "finalized_at"),
        )
        for row, (caption, key) in enumerate(fields):
            label = QLabel(caption)
            label.setObjectName("mutedLabel")
            value = QLabel("-")
            value.setObjectName("mutedLabel")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.identity_labels[key] = value
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        parent_layout.addWidget(card)

    def _build_summary_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("Ringkasan Data")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(8)
        self.summary_labels = {}
        fields = (
            ("Jumlah Harta", "jumlah_harta"),
            ("Total Harta Tahun Berjalan", "total_harta"),
            ("Jumlah Bupot", "jumlah_bupot"),
            ("Status PTKP", "status_ptkp"),
            ("PPh Terutang", "pph_terutang"),
            ("Total Pengeluaran", "total_pengeluaran"),
            ("Penghasilan Netto", "penghasilan_netto"),
            ("Selisih Rekonsiliasi", "selisih"),
        )
        for index, (caption, key) in enumerate(fields):
            row = index % 4
            column = 0 if index < 4 else 2
            label = QLabel(caption)
            label.setObjectName("mutedLabel")
            value = QLabel("-")
            value.setObjectName("mutedLabel")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, row, column)
            grid.addWidget(value, row, column + 1)
            self.summary_labels[key] = value
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)
        parent_layout.addWidget(card)


    def _build_editable_preview_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        heading = QLabel("Editable Preview Finalisasi")
        heading.setObjectName("sectionTitle")
        self.preview_edit_status = QLabel("Belum ada data")
        self.preview_edit_status.setObjectName("mutedLabel")
        header.addWidget(heading)
        header.addStretch()
        header.addWidget(self.preview_edit_status)
        layout.addLayout(header)

        note = QLabel(
            "Periksa data yang akan masuk ke snapshot FINAL. Koreksi pada mode Edited / Current "
            "akan disimpan kembali ke Worksheet tanpa mengubah Original Import."
        )
        note.setObjectName("pageSubTitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        mode_row = QHBoxLayout()
        self.preview_original_button = QPushButton("Original Import")
        self.preview_original_button.setObjectName("secondaryButton")
        self.preview_current_button = QPushButton("Edited / Current")
        self.preview_current_button.setObjectName("secondaryButton")
        self.preview_save_button = QPushButton("Simpan Koreksi Preview")
        self.preview_save_button.setObjectName("primaryButton")
        self.preview_save_button.setEnabled(False)
        self.preview_original_button.clicked.connect(
            lambda: self._set_preview_mode("original")
        )
        self.preview_current_button.clicked.connect(
            lambda: self._set_preview_mode("current")
        )
        self.preview_save_button.clicked.connect(self._save_preview_corrections)
        mode_row.addWidget(self.preview_original_button)
        mode_row.addWidget(self.preview_current_button)
        mode_row.addStretch()
        mode_row.addWidget(self.preview_save_button)
        layout.addLayout(mode_row)

        self.preview_mode = "current"
        self.preview_tabs = QTabWidget()

        self.preview_harta_table = QTableWidget(0, 10)
        self.preview_harta_table.setHorizontalHeaderLabels([
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
        self.preview_harta_table.verticalHeader().setVisible(False)
        self.preview_harta_table.setAlternatingRowColors(True)
        self.preview_harta_table.setMinimumHeight(260)
        self.preview_harta_table.itemChanged.connect(
            self._on_preview_harta_changed
        )
        optimize_table_interaction(
            self.preview_harta_table,
            column_widths={
                0: 55, 1: 100, 2: 95, 3: 190, 4: 220,
                5: 160, 6: 150, 7: 105, 8: 145, 9: 145,
            },
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )

        self.preview_bupot_table = QTableWidget(0, 25)
        self.preview_bupot_table.setHorizontalHeaderLabels([
            "NO", "JENIS BUPOT", "NO BUKPOT", "MASA", "TAHUN", "SIFAT", "STATUS",
            "NPWP PENERIMA", "NAMA PENERIMA", "FASILITAS", "JENIS PPH", "KOP",
            "BRUTO", "DPP PERSEN", "TARIF", "PENGURANG BRUTO", "PPH", "BUKTI",
            "NO BUKTI", "TANGGAL BUKTI", "NPWP PEMOTONG", "NAMA PEMOTONG",
            "TANGGAL PEMOTONGAN", "MEKANISME SP2D", "NO SP2D",
        ])
        self.preview_bupot_table.verticalHeader().setVisible(False)
        self.preview_bupot_table.setAlternatingRowColors(True)
        self.preview_bupot_table.setMinimumHeight(260)
        self.preview_bupot_table.itemChanged.connect(
            self._on_preview_bupot_changed
        )
        optimize_table_interaction(
            self.preview_bupot_table,
            column_widths={
                0: 55, 1: 110, 2: 145, 3: 70, 4: 75, 5: 110, 6: 100,
                7: 170, 8: 190, 9: 145, 10: 100, 11: 100, 12: 125,
                13: 95, 14: 85, 15: 145, 16: 125, 17: 145, 18: 190,
                19: 125, 20: 170, 21: 190, 22: 135, 23: 135, 24: 140,
            },
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )

        self.preview_tabs.addTab(self.preview_harta_table, "Harta / SIMULASI I")
        self.preview_tabs.addTab(self.preview_bupot_table, "Bupot")
        layout.addWidget(self.preview_tabs)

        parent_layout.addWidget(card)

    @staticmethod
    def _parse_preview_number(value: object) -> float:
        text = str(value or "").strip()
        if not text:
            return 0.0
        cleaned = text.replace("Rp", "").replace("rp", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                cleaned = "".join(parts)
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)

    @staticmethod
    def _preview_text(table, row, column) -> str:
        item = table.item(row, column)
        return " ".join(str(item.text() if item is not None else "").strip().split())

    def _set_preview_mode(self, mode: str):
        if mode not in {"original", "current"}:
            return
        self.preview_mode = mode
        self._render_editable_preview()

    def _sync_preview_source(self):
        if self.current_input is None:
            self._preview_harta_rows = []
            self._preview_bupot_rows = []
            return

        identity = (
            str(self.current_input.npwp or ""),
            int(self.current_input.tahun_pajak or 0),
        )
        if identity != self._preview_identity:
            self._preview_identity = identity
            self._original_bupot_rows = list(self.current_input.bupot_rows or [])
            self._preview_dirty = False

        if not self._preview_dirty:
            self._preview_harta_rows = list(
                self.current_input.harta_current_rows or []
            )
            self._preview_bupot_rows = list(self.current_input.bupot_rows or [])

    def _render_editable_preview(self):
        self._preview_rendering = True
        try:
            source = self.worksheet_source
            if self.preview_mode == "original":
                harta_rows = list(
                    getattr(source, "harta_original_rows", []) or []
                )
                bupot_rows = list(self._original_bupot_rows)
            else:
                harta_rows = list(self._preview_harta_rows)
                bupot_rows = list(self._preview_bupot_rows)

            self.preview_harta_table.clearContents()
            self.preview_harta_table.setRowCount(len(harta_rows))
            for row_index, row in enumerate(harta_rows):
                values = (
                    getattr(row, "nomor", row_index + 1),
                    getattr(row, "kode_eform", ""),
                    getattr(row, "kode_ct", ""),
                    getattr(row, "nama_harta", ""),
                    getattr(row, "nomor_akun_keterangan", ""),
                    getattr(row, "atas_nama", ""),
                    getattr(row, "nama_bank", ""),
                    getattr(row, "tahun_perolehan", ""),
                    getattr(row, "nilai_tahun_sebelumnya", 0.0),
                    getattr(row, "nilai_tahun_berjalan", 0.0),
                )
                for column, value in enumerate(values):
                    if column in {8, 9}:
                        text = self._money(value).replace("Rp ", "")
                    else:
                        text = str(value or "")
                    item = QTableWidgetItem(text)
                    if self.preview_mode == "original" or column == 0 or self.active_snapshot:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.preview_harta_table.setItem(row_index, column, item)

            self.preview_bupot_table.clearContents()
            self.preview_bupot_table.setRowCount(len(bupot_rows))
            for row_index, row in enumerate(bupot_rows):
                values = (
                    row_index + 1,
                    getattr(row, "jenis", ""),
                    getattr(row, "no_bupot", ""),
                    getattr(row, "masa", ""),
                    getattr(row, "tahun", ""),
                    getattr(row, "sifat", ""),
                    getattr(row, "status", ""),
                    getattr(row, "npwp_penerima", ""),
                    getattr(row, "nama_penerima", ""),
                    getattr(row, "fasilitas", ""),
                    getattr(row, "jenis_pph", ""),
                    getattr(row, "kop", ""),
                    getattr(row, "bruto", 0.0),
                    getattr(row, "dpp_persen", 0.0),
                    getattr(row, "tarif", 0.0),
                    getattr(row, "pengurang", 0.0),
                    getattr(row, "pph_dipotong", 0.0),
                    getattr(row, "bukti", ""),
                    getattr(row, "no_bukti", ""),
                    getattr(row, "tanggal_bukti", ""),
                    getattr(row, "npwp_pemotong", "")
                    or getattr(row, "npwp_pemberi_kerja", ""),
                    getattr(row, "nama_pemotong", ""),
                    getattr(row, "tanggal_pemotongan", ""),
                    getattr(row, "mekanisme_sp2d", ""),
                    getattr(row, "no_sp2d", ""),
                )
                for column, value in enumerate(values):
                    if column in {12, 15, 16}:
                        text = self._money(value).replace("Rp ", "")
                    else:
                        text = str(value or "")
                    item = QTableWidgetItem(text)
                    if self.preview_mode == "original" or column == 0 or self.active_snapshot:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.preview_bupot_table.setItem(row_index, column, item)

            editable = (
                self.preview_mode == "current"
                and self.current_input is not None
                and self.active_snapshot is None
            )
            self.preview_save_button.setEnabled(editable and self._preview_dirty)
            self.preview_edit_status.setText(
                "Original Import • read-only"
                if self.preview_mode == "original"
                else (
                    "FINAL • read-only"
                    if self.active_snapshot
                    else (
                        "Edited / Current • ada koreksi belum disimpan"
                        if self._preview_dirty
                        else "Edited / Current • sinkron dengan Worksheet"
                    )
                )
            )
        finally:
            self._preview_rendering = False

    def _on_preview_harta_changed(self, item):
        if (
            self._preview_rendering
            or self.preview_mode != "current"
            or self.active_snapshot is not None
            or item is None
        ):
            return
        row = item.row()
        column = item.column()
        if row < 0 or row >= len(self._preview_harta_rows) or column <= 0:
            return

        fields = (
            "nomor",
            "kode_eform",
            "kode_ct",
            "nama_harta",
            "nomor_akun_keterangan",
            "atas_nama",
            "nama_bank",
            "tahun_perolehan",
            "nilai_tahun_sebelumnya",
            "nilai_tahun_berjalan",
        )
        old = self._preview_harta_rows[row]
        try:
            if column == 7:
                value = int(self._parse_preview_number(item.text()))
            elif column in {8, 9}:
                value = float(self._parse_preview_number(item.text()))
            else:
                value = self._preview_text(self.preview_harta_table, row, column)
            self._preview_harta_rows[row] = replace(
                old, **{fields[column]: value}
            )
        except (TypeError, ValueError):
            self.toast_notification.show_message(
                "Nilai Harta pada preview tidak valid.", "warning", 3200
            )
            self._render_editable_preview()
            return

        self._preview_dirty = True
        self._render_editable_preview()

    def _on_preview_bupot_changed(self, item):
        if (
            self._preview_rendering
            or self.preview_mode != "current"
            or self.active_snapshot is not None
            or item is None
        ):
            return
        try:
            self._preview_bupot_rows = self._snapshot_preview_bupot_rows()
        except (TypeError, ValueError):
            self.toast_notification.show_message(
                "Nilai Bupot pada preview tidak valid.", "warning", 3200
            )
            self._render_editable_preview()
            return
        self._preview_dirty = True
        self._render_editable_preview()

    def _snapshot_preview_bupot_rows(self):
        from core.worksheet_pph_state import WorksheetBupotRow

        rows = []
        for row in range(self.preview_bupot_table.rowCount()):
            text = lambda col: self._preview_text(self.preview_bupot_table, row, col)
            number = lambda col: self._parse_preview_number(text(col))
            npwp_pemotong = "".join(ch for ch in text(20) if ch.isdigit())
            rows.append(
                WorksheetBupotRow(
                    jenis=text(1),
                    no_bupot=text(2),
                    masa=text(3),
                    tahun=text(4),
                    sifat=text(5),
                    status=text(6),
                    npwp_penerima="".join(ch for ch in text(7) if ch.isdigit()),
                    nama_penerima=text(8),
                    fasilitas=text(9),
                    jenis_pph=text(10),
                    kop=text(11),
                    bruto=number(12),
                    dpp_persen=number(13),
                    tarif=number(14),
                    pengurang=number(15),
                    pph_dipotong=number(16),
                    bukti=text(17),
                    no_bukti=text(18),
                    tanggal_bukti=text(19),
                    npwp_pemotong=npwp_pemotong,
                    nama_pemotong=text(21),
                    tanggal_pemotongan=text(22),
                    mekanisme_sp2d=text(23),
                    no_sp2d=text(24),
                    npwp_pemberi_kerja=npwp_pemotong,
                )
            )
        return rows

    def _save_preview_corrections(self):
        if (
            not self._preview_dirty
            or self.worksheet_source is None
            or self.active_snapshot is not None
        ):
            return

        source = self.worksheet_source
        try:
            source.harta_current_rows = list(self._preview_harta_rows)
            if hasattr(source, "harta_origin_indices") and (
                len(getattr(source, "harta_origin_indices", []))
                != len(self._preview_harta_rows)
            ):
                source.harta_origin_indices = list(
                    range(len(self._preview_harta_rows))
                )
            source.harta_mode = "current"
            if hasattr(source, "save_harta_changes"):
                source.save_harta_changes()

            if hasattr(source, "_render_bupot_rows"):
                source._render_bupot_rows(self._preview_bupot_rows)
            if hasattr(source, "save_bupot_changes"):
                result = source.save_bupot_changes()
                if result is None and self._preview_bupot_rows:
                    raise ValueError(
                        "Bupot belum dapat disimpan. Periksa validasi pada Worksheet."
                    )

            self._preview_dirty = False
            self.toast_notification.show_message(
                "Koreksi preview tersimpan ke Worksheet. Original Import tetap dipertahankan.",
                "success",
                3800,
            )
            self.refresh_page()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Koreksi Preview Belum Tersimpan",
                str(exc),
            )

    def _build_validation_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading_row = QHBoxLayout()
        heading = QLabel("Hasil Validasi Akhir")
        heading.setObjectName("sectionTitle")
        self.validation_status = QLabel("Belum diperiksa")
        self.validation_status.setObjectName("mutedLabel")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        heading_row.addWidget(self.validation_status)
        layout.addLayout(heading_row)

        self.validation_table = QTableWidget(0, 4)
        self.validation_table.setHorizontalHeaderLabels(
            ["STATUS", "KODE", "PEMERIKSAAN", "KETERANGAN"]
        )
        self.validation_table.verticalHeader().setVisible(False)
        self.validation_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.validation_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.validation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.validation_table.setAlternatingRowColors(True)
        self.validation_table.setWordWrap(False)
        self.validation_table.setMinimumHeight(240)
        optimize_table_interaction(
            self.validation_table,
            column_widths=self.VALIDATION_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        layout.addWidget(self.validation_table)
        parent_layout.addWidget(card)

    def _build_actions_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("Aksi Finalisasi")
        heading.setObjectName("sectionTitle")
        self.final_state_label = QLabel(
            "Periksa ulang untuk memastikan semua data tersimpan dan siap difinalisasi."
        )
        self.final_state_label.setObjectName("mutedLabel")
        self.final_state_label.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(self.final_state_label)

        status_actions = QHBoxLayout()
        output_actions = QHBoxLayout()

        self.recheck_button = QPushButton("Periksa Ulang")
        self.recheck_button.setObjectName("secondaryButton")
        self.finalize_button = QPushButton("Finalisasi Worksheet")
        self.finalize_button.setObjectName("primaryButton")
        self.reopen_button = QPushButton("Buka Kembali Worksheet")
        self.reopen_button.setObjectName("secondaryButton")

        self.preview_legacy_button = QPushButton("Preview Format Lama")
        self.preview_legacy_button.setObjectName("secondaryButton")
        self.preview_legacy_button.setToolTip(
            "Membuka preview Form 1770 dari snapshot FINAL tanpa menyimpan file permanen."
        )

        self.export_legacy_button = QPushButton("Export Format Lama (PDF)")
        self.export_legacy_button.setObjectName("primaryButton")
        self.export_legacy_button.setToolTip(
            "Membuat Form 1770 format lama berbentuk PDF statis dari snapshot FINAL."
        )

        self.preview_coretax_button = QPushButton("Preview Paket Coretax")
        self.preview_coretax_button.setObjectName("secondaryButton")
        self.preview_coretax_button.setToolTip(
            "Menampilkan ringkasan kategori Harta dari snapshot FINAL tanpa membuat file."
        )

        self.export_coretax_button = QPushButton("Export Paket Coretax")
        self.export_coretax_button.setObjectName("primaryButton")
        self.export_coretax_button.setToolTip(
            "Membuat Excel hanya untuk kategori Harta yang tersedia, "
            "XML jika referensinya tersedia, lalu memvalidasi paket."
        )

        self.recheck_button.clicked.connect(self.refresh_page)
        self.finalize_button.clicked.connect(self._finalize)
        self.reopen_button.clicked.connect(self._reopen)
        self.preview_legacy_button.clicked.connect(self._preview_legacy_pdf)
        self.export_legacy_button.clicked.connect(self._export_legacy_pdf)
        self.preview_coretax_button.clicked.connect(self._preview_coretax_package)
        self.export_coretax_button.clicked.connect(self._export_official_coretax)

        status_actions.addWidget(self.recheck_button)
        status_actions.addWidget(self.finalize_button)
        status_actions.addWidget(self.reopen_button)
        status_actions.addStretch()

        output_label = QLabel("Output Final")
        output_label.setObjectName("mutedLabel")
        layout.addWidget(output_label)

        output_actions.addWidget(self.preview_legacy_button)
        output_actions.addWidget(self.export_legacy_button)
        output_actions.addWidget(self.preview_coretax_button)
        output_actions.addWidget(self.export_coretax_button)
        output_actions.addStretch()

        layout.addLayout(status_actions)
        layout.addLayout(output_actions)
        parent_layout.addWidget(card)

    def _build_history_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("Riwayat Finalisasi")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["REVISION", "STATUS", "FINALIZED AT", "VOIDED AT", "HASH"]
        )
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setWordWrap(False)
        self.history_table.setMinimumHeight(175)
        optimize_table_interaction(
            self.history_table,
            column_widths=self.HISTORY_WIDTHS,
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        layout.addWidget(self.history_table)
        parent_layout.addWidget(card)

    def _build_export_history_card(self, parent_layout):
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("Riwayat Export")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        self.export_history_table = QTableWidget(0, 7)
        self.export_history_table.setHorizontalHeaderLabels(
            [
                "WAKTU",
                "REV",
                "JENIS",
                "STATUS",
                "VALIDATOR",
                "REKONSILIASI",
                "OUTPUT",
            ]
        )
        self.export_history_table.verticalHeader().setVisible(False)
        self.export_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.export_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.export_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.export_history_table.setAlternatingRowColors(True)
        self.export_history_table.setWordWrap(False)
        self.export_history_table.setMinimumHeight(180)
        optimize_table_interaction(
            self.export_history_table,
            column_widths={
                0: 150,
                1: 70,
                2: 150,
                3: 90,
                4: 100,
                5: 115,
                6: 320,
            },
            row_height=34,
            horizontal_step=18,
            vertical_step=18,
        )
        layout.addWidget(self.export_history_table)
        parent_layout.addWidget(card)

    def _render_export_history(self):
        if (
            not self.current_input
            or not self.current_input.npwp
            or not self.current_input.tahun_pajak
        ):
            self.export_history_table.setRowCount(0)
            return

        rows = self.audit_service.list_for_wp(
            self.current_input.npwp,
            self.current_input.tahun_pajak,
            limit=30,
        )
        with suspended_updates(self.export_history_table):
            self.export_history_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                values = (
                    row["created_at"] or "-",
                    f"R{row['revision']}",
                    row["export_type"] or "-",
                    row["status"] or "-",
                    row["validator_status"] or "-",
                    row["reconciliation_status"] or "-",
                    row["output_path"] or "-",
                )
                for column, value in enumerate(values):
                    self.export_history_table.setItem(
                        row_index,
                        column,
                        QTableWidgetItem(str(value)),
                    )

    @staticmethod
    def _money(value) -> str:
        try:
            return "Rp " + f"{float(value or 0):,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            return "Rp 0"

    def refresh_page(self):
        if self.worksheet_source is None:
            self.current_input = None
            self.current_validation = None
            self.active_snapshot = None
            self._render_empty_state()
            return

        self.current_input = FinalizationAdapter.from_worksheet(self.worksheet_source)
        self.current_validation = self.service.validate(self.current_input)
        if self.current_input.npwp and self.current_input.tahun_pajak:
            self.active_snapshot = self.service.get_active_snapshot(
                self.current_input.npwp, self.current_input.tahun_pajak
            )
        else:
            self.active_snapshot = None

        self._sync_preview_source()
        self._render_identity()
        self._render_summary()
        self._render_editable_preview()
        self._render_validation()
        self._render_actions()
        self._render_history()
        self._render_export_history()

    def _render_empty_state(self):
        for label in self.identity_labels.values():
            label.setText("-")
        for label in self.summary_labels.values():
            label.setText("-")
        self.validation_status.setText("Worksheet belum tersedia")
        if hasattr(self, "preview_edit_status"):
            self.preview_edit_status.setText("Worksheet belum tersedia")
            self.preview_harta_table.setRowCount(0)
            self.preview_bupot_table.setRowCount(0)
            self.preview_save_button.setEnabled(False)
        self.validation_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.export_history_table.setRowCount(0)
        self.final_state_label.setText(
            "Muat data Coretax dan selesaikan Worksheet terlebih dahulu."
        )
        self.finalize_button.setEnabled(False)
        self.reopen_button.setVisible(False)
        self.preview_legacy_button.setEnabled(False)
        self.export_legacy_button.setEnabled(False)
        self.preview_coretax_button.setEnabled(False)
        self.export_coretax_button.setEnabled(False)

    def _render_identity(self):
        data = self.current_input
        snapshot = self.active_snapshot
        self.identity_labels["nama_wp"].setText(data.nama_wp or "-")
        self.identity_labels["npwp"].setText(data.npwp or "-")
        self.identity_labels["tahun_pajak"].setText(
            str(data.tahun_pajak) if data.tahun_pajak else "-"
        )
        self.identity_labels["status"].setText("FINAL" if snapshot else "DRAFT")
        self.identity_labels["revision"].setText(
            f"Revision {snapshot['revision']}" if snapshot else "-"
        )
        self.identity_labels["finalized_at"].setText(
            str(snapshot["finalized_at"] or "-") if snapshot else "-"
        )

    def _render_summary(self):
        data = self.current_input
        harta = data.harta_current_rows or []
        analisis = data.analisis_result
        total_harta = sum(float(row.nilai_tahun_berjalan or 0) for row in harta)
        pph_terutang = data.pph_calc_result.get(
            "pph_terutang", data.pph_components.get("pph_terutang", 0.0)
        )

        self.summary_labels["jumlah_harta"].setText(f"{len(harta)} baris")
        self.summary_labels["total_harta"].setText(self._money(total_harta))
        self.summary_labels["jumlah_bupot"].setText(f"{len(data.bupot_rows)} baris")
        self.summary_labels["status_ptkp"].setText(data.status_ptkp or "-")
        self.summary_labels["pph_terutang"].setText(self._money(pph_terutang))
        self.summary_labels["total_pengeluaran"].setText(
            self._money(getattr(analisis, "total_pengeluaran", 0.0))
        )
        self.summary_labels["penghasilan_netto"].setText(
            self._money(getattr(analisis, "penghasilan_netto", 0.0))
        )
        self.summary_labels["selisih"].setText(
            self._money(getattr(analisis, "selisih_pengeluaran_vs_penghasilan", 0.0))
        )

    @staticmethod
    def _severity_text(severity):
        if severity == ValidationSeverity.ERROR:
            return "🔴 ERROR"
        if severity == ValidationSeverity.WARNING:
            return "🟡 WARNING"
        return "🟢 INFO"

    def _render_validation(self):
        validation = self.current_validation
        issues = sorted(
            validation.issues,
            key=lambda issue: {
                ValidationSeverity.ERROR: 0,
                ValidationSeverity.WARNING: 1,
                ValidationSeverity.INFO: 2,
            }[issue.severity],
        )
        with suspended_updates(self.validation_table):
            self.validation_table.setRowCount(len(issues))
            for row, issue in enumerate(issues):
                values = (
                    self._severity_text(issue.severity),
                    issue.code,
                    issue.field or "Pemeriksaan umum",
                    issue.message,
                )
                for column, value in enumerate(values):
                    self.validation_table.setItem(
                        row, column, QTableWidgetItem(str(value or "-"))
                    )

        self.validation_status.setText(
            f"{len(validation.errors)} Error • {len(validation.warnings)} Warning • {len(validation.infos)} Info"
        )

    def _render_actions(self):
        active = self.active_snapshot
        if active:
            short_hash = str(active["snapshot_hash"] or "")[:12]
            self.final_state_label.setText(
                f"FINAL • Revision {active['revision']} • Snapshot {short_hash}… • "
                "Buka kembali hanya jika Worksheet perlu dikoreksi."
            )
            self.finalize_button.setEnabled(False)
            self.reopen_button.setVisible(True)
            self.reopen_button.setEnabled(True)
            self.preview_legacy_button.setEnabled(True)
            self.export_legacy_button.setEnabled(True)
            self.preview_coretax_button.setEnabled(True)
            self.export_coretax_button.setEnabled(True)
            return

        errors = self.current_validation.errors if self.current_validation else []
        warnings = self.current_validation.warnings if self.current_validation else []
        if errors:
            self.final_state_label.setText(
                "Finalisasi diblokir. Selesaikan seluruh ERROR pada Worksheet lalu simpan perubahan."
            )
        elif warnings:
            self.final_state_label.setText(
                "Worksheet dapat difinalisasi, tetapi terdapat WARNING yang perlu dikonfirmasi."
            )
        else:
            self.final_state_label.setText(
                "Worksheet siap difinalisasi. Snapshot final akan menjadi sumber proses export berikutnya."
            )
        self.finalize_button.setEnabled(bool(self.current_validation and not errors))
        self.reopen_button.setVisible(False)
        self.preview_legacy_button.setEnabled(False)
        self.export_legacy_button.setEnabled(False)
        self.preview_coretax_button.setEnabled(False)
        self.export_coretax_button.setEnabled(False)

    def _render_history(self):
        if not self.current_input or not self.current_input.npwp or not self.current_input.tahun_pajak:
            self.history_table.setRowCount(0)
            return
        rows = self.service.list_snapshots(
            self.current_input.npwp, self.current_input.tahun_pajak
        )
        with suspended_updates(self.history_table):
            self.history_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                values = (
                    f"Revision {row['revision']}",
                    row["status"],
                    row["finalized_at"] or "-",
                    row["voided_at"] or "-",
                    str(row["snapshot_hash"] or "")[:16],
                )
                for column, value in enumerate(values):
                    self.history_table.setItem(
                        row_index, column, QTableWidgetItem(str(value))
                    )

    def _warning_confirmation(self) -> bool:
        warnings = self.current_validation.warnings if self.current_validation else []
        if not warnings:
            return True
        detail = "\n".join(f"• {item.message}" for item in warnings)
        result = QMessageBox.warning(
            self,
            "Konfirmasi Finalisasi",
            "Terdapat peringatan pada Worksheet.\n\n"
            f"{detail}\n\nTetap finalisasi?",
            QMessageBox.Cancel | QMessageBox.Yes,
            QMessageBox.Cancel,
        )
        return result == QMessageBox.Yes

    def _finalize(self):
        self.refresh_page()
        if not self.current_input or not self.current_validation:
            return
        if self.current_validation.errors:
            self.toast_notification.show_message(
                "Finalisasi diblokir karena masih terdapat ERROR.", "warning", 3600
            )
            return
        if not self._warning_confirmation():
            return

        result = self.service.finalize(self.current_input)
        if result.success:
            self.toast_notification.show_message(
                f"Worksheet berhasil difinalisasi sebagai Revision {result.revision}.",
                "success",
                3600,
            )
        else:
            self.toast_notification.show_message(
                result.message or "Worksheet gagal difinalisasi.", "error", 4200
            )
        self.refresh_page()

    def _preview_legacy_pdf(self):
        if not self.current_input or not self.active_snapshot:
            self.toast_notification.show_message(
                "Preview Format Lama hanya tersedia untuk Worksheet berstatus FINAL.",
                "warning",
                3600,
            )
            return

        revision = int(self.active_snapshot["revision"] or 0)
        try:
            with TemporaryDirectory(prefix="tax1770_preview_") as temp_dir:
                preview_path = (
                    Path(temp_dir)
                    / (
                        f"1770_preview_{self.current_input.npwp}_"
                        f"{self.current_input.tahun_pajak}_rev{revision}.pdf"
                    )
                )
                result = Legacy1770StaticPdfService().finalize_active_final(
                    self.current_input.npwp,
                    self.current_input.tahun_pajak,
                    preview_path,
                    db_path=self.service.db_path,
                )
                if not result.ok:
                    details = "\n".join(
                        f"[{issue.severity}] {issue.code}: {issue.message}"
                        for issue in result.issues
                    ) or "Preview Format Lama tidak dapat dibuat."
                    QMessageBox.warning(
                        self,
                        "Preview Format Lama Gagal",
                        details,
                    )
                    return

                dialog = LegacyPdfPreviewDialog(
                    result.output_path,
                    parent=self,
                )
                dialog.exec()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Preview Format Lama Gagal",
                str(exc),
            )

    def _export_legacy_pdf(self):
        if not self.current_input or not self.active_snapshot:
            self.toast_notification.show_message(
                "Export Format Lama hanya tersedia untuk Worksheet berstatus FINAL.",
                "warning",
                3600,
            )
            return

        revision = int(self.active_snapshot["revision"] or 0)
        suggested_name = (
            f"1770_format_lama_{self.current_input.npwp}_"
            f"{self.current_input.tahun_pajak}_rev{revision}.pdf"
        )
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Format Lama 1770",
            suggested_name,
            "PDF (*.pdf)",
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            result = Legacy1770StaticPdfService().finalize_active_final(
                self.current_input.npwp,
                self.current_input.tahun_pajak,
                output_path,
                db_path=self.service.db_path,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Export Format Lama Gagal",
                str(exc),
            )
            return

        if not result.ok:
            details = "\n".join(
                f"[{issue.severity}] {issue.code}: {issue.message}"
                for issue in result.issues
            ) or "PDF Format Lama tidak berhasil dibuat."
            self.audit_service.record(
                ExportAuditRecord(
                    npwp=self.current_input.npwp,
                    nama_wp=self.current_input.nama_wp,
                    tahun_pajak=self.current_input.tahun_pajak,
                    revision=revision,
                    export_type="FORMAT_LAMA_PDF",
                    status="FAIL",
                    output_path=str(output_path),
                    validator_status="FAIL",
                    reconciliation_status="N/A",
                    message=details,
                )
            )
            self._render_export_history()
            QMessageBox.warning(
                self,
                "Export Format Lama Gagal",
                details,
            )
            return

        self.audit_service.record(
            ExportAuditRecord(
                npwp=self.current_input.npwp,
                nama_wp=self.current_input.nama_wp,
                tahun_pajak=self.current_input.tahun_pajak,
                revision=revision,
                export_type="FORMAT_LAMA_PDF",
                status="PASS",
                output_path=str(result.output_path),
                artifact_count=result.page_count,
                validator_status="PASS",
                reconciliation_status="N/A",
                sha256=result.sha256,
                message="PDF statis terverifikasi.",
            )
        )
        self._render_export_history()

        warning_text = ""
        if result.warnings:
            warning_text = "\n\nCatatan:\n" + "\n".join(
                f"• {issue.message}"
                for issue in result.warnings
            )

        self.toast_notification.show_message(
            "Format Lama 1770 berhasil dibuat sebagai PDF statis.",
            "success",
            4200,
        )
        QMessageBox.information(
            self,
            "Export Format Lama Berhasil",
            (
                "Format Lama 1770 berhasil dibuat.\n\n"
                f"Lokasi: {result.output_path}\n"
                f"Halaman: {result.page_count}\n"
                f"Ukuran: {result.size_bytes:,} byte\n"
                "Status: PDF statis terverifikasi"
                f"{warning_text}"
            ),
        )

    def _detect_coretax_source_dir(self) -> Optional[Path]:
        """Cari folder sumber Coretax asli dari metadata Harta yang sedang difinalisasi.

        Rekonsiliasi hanya dijalankan otomatis bila seluruh source_file yang
        tercatat masih ada dan berada pada satu folder yang sama. Bila tidak,
        export tetap boleh dilakukan tetapi status rekonsiliasi menjadi SKIPPED.
        """
        if not self.current_input:
            return None

        source_files = []
        for row in self.current_input.harta_current_rows or []:
            metadata = getattr(row, "coretax_metadata", None) or {}
            raw_path = str(metadata.get("source_file") or "").strip()
            if not raw_path:
                return None
            path = Path(raw_path)
            if not path.is_file():
                return None
            source_files.append(path.resolve())

        if not source_files:
            return None

        parents = {path.parent for path in source_files}
        if len(parents) != 1:
            return None

        return next(iter(parents))

    def _preview_coretax_package(self):
        if not self.current_input or not self.active_snapshot:
            self.toast_notification.show_message(
                "Preview Paket Coretax hanya tersedia untuk Worksheet berstatus FINAL.",
                "warning",
                3600,
            )
            return

        package = ReverseCoretaxMappingService(
            db_path=self.service.db_path
        ).build_active_final(
            self.current_input.npwp,
            self.current_input.tahun_pajak,
        )

        if not package.can_export:
            details = "\n".join(
                f"[{issue.severity}] {issue.code}: {issue.message}"
                for issue in package.issues
                if issue.severity in {"ERROR", "WARNING"}
            ) or "Snapshot FINAL belum siap untuk dipreview sebagai Paket Coretax."
            QMessageBox.warning(
                self,
                "Preview Paket Coretax Gagal",
                details,
            )
            return

        dialog = CoretaxPackagePreviewDialog(
            package,
            parent=self,
        )
        dialog.exec()

    def _export_official_coretax(self):
        if not self.current_input or not self.active_snapshot:
            self.toast_notification.show_message(
                "Export Coretax hanya tersedia untuk Worksheet berstatus FINAL.",
                "warning",
                3600,
            )
            return

        template_dir = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Template Excel Coretax Asli",
        )
        if not template_dir:
            return

        output_parent = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Penyimpanan Paket Coretax",
        )
        if not output_parent:
            return

        revision = int(self.active_snapshot["revision"] or 0)
        output_dir = (
            Path(output_parent)
            / (
                f"coretax_official_{self.current_input.npwp}_"
                f"{self.current_input.tahun_pajak}_rev{revision}"
            )
        )

        try:
            export_result = OfficialCoretaxPackageExporter(
                template_dir
            ).export_active_final(
                self.current_input.npwp,
                self.current_input.tahun_pajak,
                output_dir,
                db_path=self.service.db_path,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Export Paket Coretax Gagal",
                str(exc),
            )
            return

        if not export_result.ok:
            details = "\n".join(
                f"[{issue.severity}] {issue.code}: {issue.message}"
                for issue in export_result.issues
            ) or "Exporter tidak menghasilkan paket yang valid."
            self.audit_service.record(
                ExportAuditRecord(
                    npwp=self.current_input.npwp,
                    nama_wp=self.current_input.nama_wp,
                    tahun_pajak=self.current_input.tahun_pajak,
                    revision=revision,
                    export_type="PAKET_CORETAX",
                    status="FAIL",
                    output_path=str(output_dir),
                    validator_status="FAIL",
                    reconciliation_status="NOT_RUN",
                    message=details,
                )
            )
            self._render_export_history()
            QMessageBox.warning(
                self,
                "Export Paket Coretax Gagal",
                details,
            )
            return

        validation = OfficialCoretaxPackageValidator().validate(output_dir)
        if not validation.ok:
            details = "\n".join(
                f"[{issue.severity}] {issue.code}: {issue.message}"
                for issue in validation.errors
            ) or "Validator paket menemukan ketidaksesuaian."
            self.audit_service.record(
                ExportAuditRecord(
                    npwp=self.current_input.npwp,
                    nama_wp=self.current_input.nama_wp,
                    tahun_pajak=self.current_input.tahun_pajak,
                    revision=revision,
                    export_type="PAKET_CORETAX",
                    status="FAIL",
                    output_path=str(output_dir),
                    validator_status="FAIL",
                    reconciliation_status="NOT_RUN",
                    message=details,
                )
            )
            self._render_export_history()
            QMessageBox.warning(
                self,
                "Validasi Paket Coretax Gagal",
                details,
            )
            return

        source_dir = self._detect_coretax_source_dir()
        reconciliation_status = "SKIPPED"
        reconciliation_detail = (
            "Sumber Coretax asli tidak tersedia pada lokasi import terakhir."
        )

        if source_dir is not None:
            reconciliation = PhysicalSourceExportReconciler().reconcile(
                source_dir,
                output_dir,
            )
            if not reconciliation.ok:
                details = "\n".join(
                    (
                        f"[{issue.severity}] {issue.code}"
                        + (f" [{issue.category}]" if issue.category else "")
                        + (f" baris {issue.row_number}" if issue.row_number else "")
                        + (f" field {issue.field_name}" if issue.field_name else "")
                        + f": {issue.message}"
                    )
                    for issue in reconciliation.errors
                ) or "Ditemukan perbedaan antara sumber Coretax dan hasil export."
                QMessageBox.warning(
                    self,
                    "Rekonsiliasi Paket Coretax Gagal",
                    (
                        "Paket berhasil dibuat dan lolos validator struktur, "
                        "tetapi isi hasil export berbeda dari sumber Coretax.\n\n"
                        f"{details}\n\nLokasi paket: {output_dir}"
                    ),
                )
                return

            reconciliation_status = "PASS"
            reconciliation_detail = (
                f"Sumber dibandingkan otomatis: {source_dir}"
            )

        manifest_path = output_dir / "manifest.json"
        package_sha = ""
        if manifest_path.is_file():
            import hashlib
            package_sha = hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest()

        self.audit_service.record(
            ExportAuditRecord(
                npwp=self.current_input.npwp,
                nama_wp=self.current_input.nama_wp,
                tahun_pajak=self.current_input.tahun_pajak,
                revision=revision,
                export_type="PAKET_CORETAX",
                status="PASS",
                output_path=str(output_dir),
                artifact_count=(
                    len(export_result.excel_result.files)
                    + len(export_result.xml_result.files)
                ),
                validator_status="PASS",
                reconciliation_status=reconciliation_status,
                sha256=package_sha,
                message=reconciliation_detail,
            )
        )
        self._render_export_history()

        self.toast_notification.show_message(
            (
                "Paket Coretax berhasil dibuat, lolos validasi"
                + (
                    " dan rekonsiliasi sumber."
                    if reconciliation_status == "PASS"
                    else "."
                )
            ),
            "success",
            4200,
        )
        QMessageBox.information(
            self,
            "Export Paket Coretax Berhasil",
            (
                "Paket Coretax berhasil dibuat dan lolos validasi.\n\n"
                f"Lokasi: {output_dir}\n"
                f"Isi: {len(export_result.excel_result.files)} Excel + "
                f"{len(export_result.xml_result.files)} XML + manifest.json\n"
                f"Rekonsiliasi sumber: {reconciliation_status}\n"
                f"{reconciliation_detail}"
            ),
        )

    def _reopen(self):
        snapshot = self.active_snapshot
        if not snapshot:
            return
        result = QMessageBox.question(
            self,
            "Buka Kembali Worksheet",
            f"Snapshot Final Revision {snapshot['revision']} akan dibatalkan.\n\n"
            "Snapshot tidak akan dihapus dan tetap tersimpan dalam riwayat. "
            "Worksheet dapat diedit kembali setelah proses ini.\n\nLanjutkan?",
            QMessageBox.Cancel | QMessageBox.Yes,
            QMessageBox.Cancel,
        )
        if result != QMessageBox.Yes:
            return

        ok = self.service.void_snapshot(
            int(snapshot["id"]), "Dibuka kembali oleh pengguna"
        )
        if ok:
            self.toast_notification.show_message(
                f"Worksheet dibuka kembali. Revision {snapshot['revision']} tetap tersimpan sebagai VOID.",
                "success",
                4200,
            )
        else:
            self.toast_notification.show_message(
                "Snapshot tidak dapat dibuka kembali.", "error", 3600
            )
        self.refresh_page()
