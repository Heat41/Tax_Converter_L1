import os
import sys
from pathlib import Path

# Base Path Project / Bundle
BASE_DIR = Path(__file__).resolve().parent.parent

# Application Settings
APP_NAME = "TAX_CONVERTER L-1"
APP_VERSION = "1.0.0"
APP_SLUG = "TaxConverterL1"
DEFAULT_TAHUN_PAJAK = 2025

# Runtime mode
IS_FROZEN = bool(getattr(sys, "frozen", False))

# Database Configuration
#
# Development:
#   <repo>/data/tax_converter.db
#
# Packaged Windows app:
#   %LOCALAPPDATA%/TaxConverterL1/data/tax_converter.db
#
# Database user tidak diletakkan di folder instalasi agar:
# - tidak terkena permission Program Files;
# - tidak ikut tertimpa saat aplikasi di-update;
# - build baru tetap memakai data user yang sama.
if IS_FROZEN:
    local_app_data = Path(
        os.environ.get(
            "LOCALAPPDATA",
            Path.home() / "AppData" / "Local",
        )
    )
    APP_DATA_DIR = local_app_data / APP_SLUG
else:
    APP_DATA_DIR = BASE_DIR

SQLITE_DB_PATH = APP_DATA_DIR / "data" / "tax_converter.db"
