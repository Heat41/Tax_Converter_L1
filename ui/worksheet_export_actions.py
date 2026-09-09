from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton

from core.finalization_adapter import FinalizationAdapter
from core.worksheet_archive_exporter_polished import PolishedWorksheetArchiveExporter


class WorksheetExportActions:
    """Composition helper Stage 8B.2 untuk aksi export Kertas Kerja.

    Tidak menambah subclass baru pada rantai WorksheetPage. Tombol dipasang ke
    layout Worksheet yang sudah ada dan exporter membaca saved domain state lewat
    FinalizationAdapter.
    """

    def __init__(self, worksheet, parent=None):
        self.worksheet = worksheet
        self.parent = parent or worksheet
        self.exporter = PolishedWorksheetArchiveExporter()
        self._install()

    def _install(self):
        layout = self.worksheet.layout()
        if layout is None:
            return

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        label = QLabel("Arsip Kertas Kerja")
        label.setObjectName("sectionTitle")

        self.excel_button = QPushButton("Export Excel")
        self.excel_button.setObjectName("secondaryButton")
        self.excel_button.setCursor(Qt.PointingHandCursor)
        self.excel_button.setToolTip(
            "Export Kertas Kerja ke .xlsx. File dapat dibuka di Excel dan diimpor kembali ke aplikasi."
        )
        self.excel_button.clicked.connect(self.export_excel)

        self.pdf_button = QPushButton("Export PDF")
        self.pdf_button.setObjectName("secondaryButton")
        self.pdf_button.setCursor(Qt.PointingHandCursor)
        self.pdf_button.setToolTip(
            "Export versi arsip baca-saja Kertas Kerja. Ini bukan Form 1770 Format Lama."
        )
        self.pdf_button.clicked.connect(self.export_pdf)

        row.addWidget(label)
        row.addStretch()
        row.addWidget(self.excel_button)
        row.addWidget(self.pdf_button)

        # Worksheet base: title, subtitle, tabs. Letakkan aksi tepat sebelum tabs.
        insert_index = max(0, layout.count() - 1)
        layout.insertLayout(insert_index, row)

    def _data(self):
        return FinalizationAdapter.from_worksheet(self.worksheet)

    def _default_name(self, extension: str) -> str:
        data = self._data()
        safe_name = "_".join(str(data.nama_wp or "WP").split())
        return f"Kertas_Kerja_{safe_name}_{data.tahun_pajak or 'Tahun'}.{extension}"

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Export Kertas Kerja ke Excel",
            self._default_name("xlsx"),
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        try:
            result = self.exporter.export_excel(self._data(), Path(path))
        except Exception as exc:
            QMessageBox.warning(self.parent, "Export Excel Gagal", str(exc))
            return
        self._notify_success(
            f"Kertas Kerja berhasil diekspor ke Excel: {result.output_path.name}"
        )

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Export Kertas Kerja ke PDF",
            self._default_name("pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            result = self.exporter.export_pdf(self._data(), Path(path))
        except Exception as exc:
            QMessageBox.warning(self.parent, "Export PDF Gagal", str(exc))
            return
        self._notify_success(
            f"Kertas Kerja berhasil diekspor ke PDF: {result.output_path.name}"
        )

    def _notify_success(self, message: str):
        toast = getattr(self.worksheet, "toast_notification", None)
        if toast is not None:
            toast.show_message(message, "success", 3600)
        else:
            QMessageBox.information(self.parent, "Export Berhasil", message)
