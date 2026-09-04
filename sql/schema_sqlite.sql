-- =============================================================================
-- PROYEK: Tax_Converter_L1
-- SKEMA DATABASE: SQLite Unified Asset Model (Phase 1 Final)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. TABEL MASTER WAJIB PAJAK (master_wp)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_wp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npwp TEXT UNIQUE NOT NULL CHECK(length(npwp) = 16 AND npwp NOT GLOB '*[^0-9]*'),
    nama_wp TEXT NOT NULL,
    tahun_pajak INTEGER NOT NULL DEFAULT 2025 CHECK(tahun_pajak >= 2000 AND tahun_pajak <= 2100),
    status_ptkp TEXT NOT NULL DEFAULT 'TK/0',
    status_proses TEXT NOT NULL DEFAULT 'BELUM_IMPOR' CHECK(status_proses IN ('BELUM_IMPOR', 'DRAFT', 'FINAL')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_master_wp_npwp ON master_wp(npwp);
CREATE INDEX IF NOT EXISTS idx_master_wp_tahun ON master_wp(tahun_pajak);

-- -----------------------------------------------------------------------------
-- 2. TABEL BATCH IMPORT (import_batches) - Mendukung Re-Import & Snapshot
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wp_id INTEGER NOT NULL,
    batch_number INTEGER NOT NULL DEFAULT 1,
    source_files TEXT, -- Format JSON ringkasan file-file sumber
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'ARCHIVED', 'REPLACED')),
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_import_batches_wp ON import_batches(wp_id);

-- -----------------------------------------------------------------------------
-- 3. TABEL MASTER REFERENSI KODE HARTA (ref_kode_harta)
-- Mapping 35 Kode E-Form Lama (3-digit) <-> Coretax (4-digit)
-- Mendukung relasi 1:1, 1:N, dan N:1
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ref_kode_harta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_eform TEXT NOT NULL,
    kode_coretax TEXT NOT NULL,
    nama_harta_lama TEXT NOT NULL,
    nama_harta_coretax TEXT NOT NULL,
    kategori_l1 TEXT NOT NULL CHECK(kategori_l1 IN ('KAS', 'PIUTANG', 'INVESTASI', 'BERGERAK', 'HTB', 'LAINNYA')),
    is_primary_mapping INTEGER NOT NULL DEFAULT 1 CHECK(is_primary_mapping IN (0, 1)),
    catatan_mapping TEXT
);

CREATE INDEX IF NOT EXISTS idx_ref_eform ON ref_kode_harta(kode_eform);
CREATE INDEX IF NOT EXISTS idx_ref_coretax ON ref_kode_harta(kode_coretax);
CREATE INDEX IF NOT EXISTS idx_ref_kategori ON ref_kode_harta(kategori_l1);

-- -----------------------------------------------------------------------------
-- 4. TABEL UNIFIED ASSET (harta_l1_items)
-- Menyimpan seluruh 6 Kategori Coretax L-1 dengan pemisahan Original vs Current Value
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS harta_l1_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wp_id INTEGER NOT NULL,
    import_batch_id INTEGER,
    kategori_l1 TEXT NOT NULL CHECK(kategori_l1 IN ('KAS', 'PIUTANG', 'INVESTASI', 'BERGERAK', 'HTB', 'LAINNYA')),
    kode_harta TEXT NOT NULL,
    tahun_perolehan INTEGER NOT NULL CHECK(tahun_perolehan >= 1900 AND tahun_perolehan <= 2100),

    -- Field KAS & SETARA KAS
    nomor_akun TEXT,
    atas_nama TEXT,
    nama_bank_institusi TEXT,
    lokasi_negara TEXT,
    saldo_original REAL DEFAULT 0.0,
    saldo_current REAL DEFAULT 0.0,

    -- Field PIUTANG
    nomor_identitas_pihak_ketiga TEXT,
    nama_pihak_ketiga TEXT,
    nilai_piutang_original REAL DEFAULT 0.0,
    nilai_piutang_current REAL DEFAULT 0.0,
    saldo_piutang_original REAL DEFAULT 0.0,
    saldo_piutang_current REAL DEFAULT 0.0,

    -- Field INVESTASI / SURAT BERHARGA
    nama_institusi TEXT,
    nomor_akun_bukti TEXT,
    biaya_perolehan_original REAL DEFAULT 0.0,
    biaya_perolehan_current REAL DEFAULT 0.0,
    nilai_saat_ini_original REAL DEFAULT 0.0,
    nilai_saat_ini_current REAL DEFAULT 0.0,

    -- Field HARTA BERGERAK
    merek_model TEXT,
    nomor_polisi_registrasi TEXT,
    jenis_kepemilikan TEXT CHECK(jenis_kepemilikan IS NULL OR jenis_kepemilikan IN ('TAXPAYER', 'OTHER')),
    npwp_pemilik TEXT,
    nama_pemilik TEXT,

    -- Field HARTA TIDAK BERGERAK (HTB)
    lokasi_alamat TEXT,
    luas_tanah TEXT,
    luas_bangunan TEXT,
    sumber_kepemilikan TEXT,
    nomor_sertifikat TEXT,

    -- Field HARTA LAINNYA
    informasi_tambahan TEXT,

    -- Field UMUM & METADATA
    keterangan_pps TEXT,
    keterangan_tambahan TEXT,
    source_file TEXT,
    source_category TEXT,
    is_edited INTEGER NOT NULL DEFAULT 0 CHECK(is_edited IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE RESTRICT,
    FOREIGN KEY (import_batch_id) REFERENCES import_batches(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_harta_wp_id ON harta_l1_items(wp_id);
CREATE INDEX IF NOT EXISTS idx_harta_kategori ON harta_l1_items(kategori_l1);
CREATE INDEX IF NOT EXISTS idx_harta_kode ON harta_l1_items(kode_harta);
CREATE INDEX IF NOT EXISTS idx_harta_active ON harta_l1_items(is_active);

-- -----------------------------------------------------------------------------
-- 5. TABEL AUDIT TRAIL KOREKSI (audit_trail_koreksi)
-- Mencatat seluruh riwayat mutasi & koreksi data per sel/field secara kronologis
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_trail_koreksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wp_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    nama_kolom TEXT NOT NULL,
    nilai_lama TEXT,
    nilai_baru TEXT,
    action TEXT NOT NULL DEFAULT 'UPDATE' CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'RE_IMPORT_RESET', 'RE_IMPORT_PRESERVE')),
    source TEXT NOT NULL DEFAULT 'USER_EDIT' CHECK(source IN ('CORETAX_IMPORT', 'USER_EDIT', 'SYSTEM_CALCULATION')),
    waktu_koreksi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    keterangan TEXT,
    FOREIGN KEY (wp_id) REFERENCES master_wp(id) ON DELETE RESTRICT,
    FOREIGN KEY (asset_id) REFERENCES harta_l1_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audit_wp_id ON audit_trail_koreksi(wp_id);
CREATE INDEX IF NOT EXISTS idx_audit_asset_id ON audit_trail_koreksi(asset_id);
CREATE INDEX IF NOT EXISTS idx_audit_waktu ON audit_trail_koreksi(waktu_koreksi);
