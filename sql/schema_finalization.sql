-- =============================================================================
-- PROYEK: Tax_Converter_L1
-- SKEMA DATABASE: STAGE 8A.1 - FINALISASI & VALIDASI AKHIR
-- =============================================================================

CREATE TABLE IF NOT EXISTS worksheet_final_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npwp TEXT NOT NULL,
    nama_wp TEXT NOT NULL,
    tahun_pajak INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('FINAL', 'VOID')),
    snapshot_schema_version INTEGER NOT NULL DEFAULT 1,
    snapshot_json TEXT NOT NULL,
    validation_json TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    finalized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    voided_at TIMESTAMP NULL,
    void_reason TEXT NULL,
    UNIQUE(npwp, tahun_pajak, revision)
);

CREATE INDEX IF NOT EXISTS idx_wfs_npwp_tahun ON worksheet_final_snapshots(npwp, tahun_pajak);
CREATE INDEX IF NOT EXISTS idx_wfs_status ON worksheet_final_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_wfs_hash ON worksheet_final_snapshots(snapshot_hash);
