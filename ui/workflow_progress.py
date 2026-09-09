from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout


class WorkflowProgress(QFrame):
    """Indikator tahapan kerja dari impor sampai finalisasi."""

    STAGES = (
        "Impor Coretax",
        "Harta",
        "PPh",
        "Analisis",
        "Finalisasi",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(7)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("Progress Pengerjaan")
        title.setObjectName("cardTitle")
        self.status_label = QLabel("Mulai")
        self.status_label.setObjectName("mutedLabel")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.STAGES))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Belum dimulai")
        self.progress_bar.setMinimumHeight(16)
        layout.addWidget(self.progress_bar)

        stage_row = QHBoxLayout()
        stage_row.setContentsMargins(0, 0, 0, 0)
        stage_row.setSpacing(6)
        self.stage_labels = []
        for stage in self.STAGES:
            label = QLabel(stage)
            label.setObjectName("mutedLabel")
            label.setAlignment(Qt.AlignCenter)
            stage_row.addWidget(label, 1)
            self.stage_labels.append(label)
        layout.addLayout(stage_row)

    def set_step(self, step: int) -> None:
        step = max(0, min(int(step), len(self.STAGES)))
        self.progress_bar.setValue(step)

        if step <= 0:
            self.status_label.setText("Mulai")
            self.progress_bar.setFormat("Belum dimulai")
        else:
            current = self.STAGES[step - 1]
            self.status_label.setText(f"Tahap {step}/{len(self.STAGES)} • {current}")
            self.progress_bar.setFormat(f"{step}/{len(self.STAGES)} • {current}")

        for index, label in enumerate(self.stage_labels, start=1):
            font = label.font()
            font.setBold(index == step)
            label.setFont(font)
