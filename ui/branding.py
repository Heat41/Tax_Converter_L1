from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


APP_ICON_FILENAME = "tax_converter_l1.ico"


def app_icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "resources"
        / "branding"
        / APP_ICON_FILENAME
    )


def load_app_icon() -> QIcon:
    path = app_icon_path()
    if not path.is_file():
        return QIcon()
    return QIcon(str(path))
