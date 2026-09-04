import os
import sqlite3
from pathlib import Path
from typing import Optional
from config.settings import SQLITE_DB_PATH
from core.seeder import seed_ref_kode_harta

SCHEMA_FILE_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema_sqlite.sql"

def get_db_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Mengembalikan koneksi database SQLite terkonfigurasi dengan Foreign Keys & Row Factory."""
    target_path = Path(db_path) if db_path else SQLITE_DB_PATH
    
    if target_path != Path(":memory:"):
        os.makedirs(target_path.parent, exist_ok=True)
        
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_database(db_path: Optional[Path | str] = None) -> None:
    """Inisialisasi tabel SQLite dari file DDL schema_sqlite.sql dan seeding data master."""
    conn = get_db_connection(db_path)
    
    # 1. Jalankan Skema DDL
    with open(SCHEMA_FILE_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    
    # 2. Seed Master Reference Code (35 Mapping E-Form <-> Coretax)
    seed_ref_kode_harta(conn)
    
    conn.commit()
    conn.close()
    print("Database SQLite & Master Seeder berhasil diinisialisasi.")