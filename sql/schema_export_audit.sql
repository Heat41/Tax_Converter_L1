CREATE TABLE IF NOT EXISTS export_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npwp TEXT NOT NULL,
    nama_wp TEXT NOT NULL DEFAULT '',
    tahun_pajak INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    export_type TEXT NOT NULL,
    status TEXT NOT NULL,
    output_path TEXT NOT NULL DEFAULT '',
    artifact_count INTEGER NOT NULL DEFAULT 0,
    validator_status TEXT NOT NULL DEFAULT '',
    reconciliation_status TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_export_audit_wp_year
ON export_audit_log(npwp, tahun_pajak, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_export_audit_created
ON export_audit_log(created_at DESC);
