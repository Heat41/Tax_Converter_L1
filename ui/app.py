import sys

from PySide6.QtWidgets import QApplication

from config.database import init_database
from config.settings import APP_NAME, APP_VERSION
from ui.branding import load_app_icon
from ui.main_window_workflow import MainWindow


def main():
    init_database()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("TaxConverterL1")
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
