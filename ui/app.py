import sys

from PySide6.QtWidgets import QApplication

from config.database import init_database
from config.settings import APP_NAME, APP_VERSION
from ui.main_window import MainWindow


def main():
    init_database()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("TaxConverterL1")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
