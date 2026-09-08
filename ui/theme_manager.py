from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui.theme import stylesheet_for


SETTINGS_ORGANIZATION = "TaxConverterL1"
SETTINGS_APPLICATION = "TaxConverterL1"
THEME_KEY = "appearance/theme"
SUPPORTED_THEMES = {"light", "dark"}
DEFAULT_THEME = "light"


def normalize_theme(value: object) -> str:
    theme = str(value or DEFAULT_THEME).strip().lower()
    return theme if theme in SUPPORTED_THEMES else DEFAULT_THEME


def get_saved_theme() -> str:
    settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
    return normalize_theme(settings.value(THEME_KEY, DEFAULT_THEME))


def save_theme(theme: object) -> str:
    normalized = normalize_theme(theme)
    settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
    settings.setValue(THEME_KEY, normalized)
    settings.sync()
    return normalized


def apply_theme(theme: object, *, persist: bool = False) -> str:
    normalized = normalize_theme(theme)
    app = QApplication.instance()
    if app is not None:
        app.setProperty("appTheme", normalized)
        app.setStyleSheet(stylesheet_for(normalized))
    if persist:
        save_theme(normalized)
    return normalized
