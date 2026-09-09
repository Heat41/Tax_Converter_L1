from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.finalization import FinalizationService, ValidationSeverity
from core.finalization_adapter import FinalizationAdapter
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
        self.current_input = None
        self.current_validation = None
        self.active_snapshot = None

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
        self._build_validation_card(content_layout)
        self._build_actions_card(content_layout)
        self._build_history_card(content_layout)
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

        actions = QHBoxLayout()
        self.recheck_button = QPushButton("Periksa Ulang")
        self.recheck_button.setObjectName("secondaryButton")
        self.finalize_button = QPushButton("Finalisasi Worksheet")
        self.finalize_button.setObjectName("primaryButton")
        self.reopen_button = QPushButton("Buka Kembali Worksheet")
        self.reopen_button.setObjectName("secondaryButton")

        self.recheck_button.clicked.connect(self.refresh_page)
        self.finalize_button.clicked.connect(self._finalize)
        self.reopen_button.clicked.connect(self._reopen)

        actions.addWidget(self.recheck_button)
        actions.addWidget(self.finalize_button)
        actions.addWidget(self.reopen_button)
        actions.addStretch()
        layout.addLayout(actions)
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

        self._render_identity()
        self._render_summary()
        self._render_validation()
        self._render_actions()
        self._render_history()

    def _render_empty_state(self):
        for label in self.identity_labels.values():
            label.setText("-")
        for label in self.summary_labels.values():
            label.setText("-")
        self.validation_status.setText("Worksheet belum tersedia")
        self.validation_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.final_state_label.setText(
            "Muat data Coretax dan selesaikan Worksheet terlebih dahulu."
        )
        self.finalize_button.setEnabled(False)
        self.reopen_button.setVisible(False)

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
