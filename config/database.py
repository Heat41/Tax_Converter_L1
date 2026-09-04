import os
import sqlite3
from config.settings import SQLITE_DB_PATH

def get_db_connection():
    """Mengembalikan koneksi database SQLite."""
    # Pastikan direktori folder data tersedia
    os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Mengembalikan hasil query sebagai dict/row
    conn.execute("PRAGMA foreign_keys = ON;") # Aktifkan fitur Foreign Key
    return conn

def init_database():
    """Inisialisasi tabel-tabel SQLite otomatis saat aplikasi pertama kali dijalankan."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabel Master Wajib Pajak (WP)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_wp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npwp TEXT UNIQUE NOT NULL,
            nama_wp TEXT NOT NULL,
            tahun_pajak INTEGER DEFAULT 2025,
            status_pengerjaan TEXT DEFAULT 'Belum Impor',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Tabel Konsolidasi L-1 Sub-Tab 1: Kas dan Setara Kas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_kas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            nama_harta TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 3. Tabel Konsolidasi L-1 Sub-Tab 2: Piutang
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_piutang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            nama_peminjam TEXT,
            npwp_peminjam TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 4. Tabel Konsolidasi L-1 Sub-Tab 3: Investasi / Surat Berharga
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_investasi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            nama_harta TEXT,
            penerbit_saham TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 5. Tabel Konsolidasi L-1 Sub-Tab 4: Harta Bergerak
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_bergerak (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            nama_harta TEXT,
            merek_type TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 6. Tabel Konsolidasi L-1 Sub-Tab 5: Harta Tidak Bergerak (HTB)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_htb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            jenis_harta TEXT,
            lokasi_alamat TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 7. Tabel Konsolidasi L-1 Sub-Tab 6: Harta Lainnya
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harta_l1_lainnya (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            kode_harta TEXT NOT NULL,
            nama_harta TEXT,
            tahun_perolehan INTEGER,
            harga_perolehan REAL DEFAULT 0.00,
            keterangan TEXT,
            is_edited INTEGER DEFAULT 0,
            nilai_asal_coretax REAL DEFAULT 0.00,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    # 8. Tabel Audit Trail (Correction Log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail_koreksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_id INTEGER NOT NULL,
            tabel_sumber TEXT NOT NULL,
            row_id INTEGER NOT NULL,
            nama_kolom TEXT NOT NULL,
            nilai_lama TEXT,
            nilai_baru TEXT,
            waktu_koreksi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()
    print("Database SQLite berhasil diinisialisasi.")