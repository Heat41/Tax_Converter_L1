-- =============================================================================
-- WORKSHEET PENGHASILAN & PPh
-- State manual dipisahkan dari model Harta L-1.
-- =============================================================================

CREATE TABLE IF NOT EXISTS worksheet_pph_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npwp TEXT NOT NULL,
    tahun_pajak INTEGER NOT NULL CHECK(tahun_pajak >= 2000 AND tahun_pajak <= 2100),
    bupot_rows_json TEXT NOT NULL DEFAULT '[]',
    components_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(npwp, tahun_pajak)
);

CREATE INDEX IF NOT EXISTS idx_worksheet_pph_npwp_tahun
ON worksheet_pph_states(npwp, tahun_pajak);
