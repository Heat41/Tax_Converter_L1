from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ui.main_window import MainWindow as BaseMainWindow
from ui.workflow_progress import WorkflowProgress


class MainWindow(BaseMainWindow):
    """MainWindow dengan progress workflow dan shortcut Analisis -> Finalisasi.

    Base MainWindow tetap dipertahankan agar Stage 8A.2 yang sudah stabil tidak
    perlu direfaktor besar. Kelas ini hanya menambahkan navigasi workflow.
    """

    def __init__(self):
        super().__init__()
        self._install_workflow_progress()
        self._install_finalization_shortcut()
        self._update_workflow_progress("dashboard")

    def _install_workflow_progress(self):
        self.workflow_progress = WorkflowProgress(self.content)
        content_layout = self.content.layout()
        content_layout.setSpacing(12)
        content_layout.insertWidget(0, self.workflow_progress)

        worksheet = self.pages.get("worksheet")
        tabs = getattr(worksheet, "tabs", None)
        if tabs is not None:
            tabs.currentChanged.connect(self._on_worksheet_tab_changed)

    def _install_finalization_shortcut(self):
        worksheet = self.pages.get("worksheet")
        save_button = getattr(worksheet, "save_reconciliation_button", None)
        if save_button is None or save_button.parentWidget() is None:
            return

        parent_layout = save_button.parentWidget().layout()
        if parent_layout is None:
            return

        self.analysis_finalization_button = QPushButton("Lanjut ke Finalisasi →")
        self.analysis_finalization_button.setObjectName("secondaryButton")
        self.analysis_finalization_button.setCursor(Qt.PointingHandCursor)
        self.analysis_finalization_button.setMinimumWidth(190)
        self.analysis_finalization_button.setToolTip(
            "Buka halaman Finalisasi. Perubahan yang belum disimpan tetap akan diblokir oleh validasi."
        )
        self.analysis_finalization_button.clicked.connect(
            lambda: self._show_page("finalisasi")
        )
        parent_layout.addWidget(
            self.analysis_finalization_button,
            alignment=Qt.AlignLeft,
        )

    def _show_page(self, page_key):
        super()._show_page(page_key)
        if hasattr(self, "workflow_progress"):
            self._update_workflow_progress(page_key)

    def _on_worksheet_tab_changed(self, _index):
        if self.stack.currentWidget() is self.pages.get("worksheet"):
            self._update_workflow_progress("worksheet")

    def _update_workflow_progress(self, page_key: str):
        if not hasattr(self, "workflow_progress"):
            return

        if page_key == "pengaturan":
            self.workflow_progress.hide()
            return

        self.workflow_progress.show()

        if page_key == "dashboard":
            step = 0
        elif page_key == "import":
            step = 1
        elif page_key == "finalisasi":
            step = 5
        elif page_key == "worksheet":
            worksheet = self.pages.get("worksheet")
            tab_index = getattr(getattr(worksheet, "tabs", None), "currentIndex", lambda: 0)()
            # Tab 0 Harta, 1 PPh, 2 Analisis, tab berikutnya tetap dianggap
            # berada pada tahap Analisis/review sebelum Finalisasi.
            if tab_index <= 0:
                step = 2
            elif tab_index == 1:
                step = 3
            else:
                step = 4
        else:
            step = 0

        self.workflow_progress.set_step(step)
