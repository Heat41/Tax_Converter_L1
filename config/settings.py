import os
from pathlib import Path

# Base Path Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration (SQLite Standalone)
SQLITE_DB_PATH = BASE_DIR / "data" / "tax_converter.db"

# Application Settings
APP_NAME = "Tax_Converter_L1"
APP_VERSION = "1.0.0"
DEFAULT_TAHUN_PAJAK = 2025