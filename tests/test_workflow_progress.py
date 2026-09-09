import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.main_window_workflow import MainWindow
from ui.workflow_progress import WorkflowProgress


def _app():
    return QApplication.instance() or QApplication([])


def test_workflow_progress_steps():
    _app()
    widget = WorkflowProgress()

    widget.set_step(1)
    assert widget.progress_bar.value() == 1
    assert "Impor Coretax" in widget.status_label.text()

    widget.set_step(4)
    assert widget.progress_bar.value() == 4
    assert "Analisis" in widget.status_label.text()

    widget.set_step(5)
    assert widget.progress_bar.value() == 5
    assert "Finalisasi" in widget.status_label.text()


def test_main_window_has_analysis_finalization_shortcut():
    _app()
    window = MainWindow()
    try:
        assert hasattr(window, "analysis_finalization_button")
        assert "Finalisasi" in window.analysis_finalization_button.text()
        assert window.workflow_progress is not None
    finally:
        window.close()


def test_workflow_progress_tracks_worksheet_tabs():
    _app()
    window = MainWindow()
    try:
        window._show_page("worksheet")
        worksheet = window.pages["worksheet"]

        worksheet.tabs.setCurrentIndex(0)
        assert window.workflow_progress.progress_bar.value() == 2

        worksheet.tabs.setCurrentIndex(1)
        assert window.workflow_progress.progress_bar.value() == 3

        worksheet.tabs.setCurrentIndex(2)
        assert window.workflow_progress.progress_bar.value() == 4

        window._show_page("finalisasi")
        assert window.workflow_progress.progress_bar.value() == 5
    finally:
        window.close()
