from pathlib import Path

from config.database import init_database
from core.export_audit import ExportAuditRecord, ExportAuditService


def test_export_audit_records_and_lists_wp_history(tmp_path):
    db_path = tmp_path / "audit.db"
    init_database(db_path)
    service = ExportAuditService(db_path=db_path)

    record_id = service.record(
        ExportAuditRecord(
            npwp="6101015612710001",
            nama_wp="EVY BACHTIAR",
            tahun_pajak=2025,
            revision=5,
            export_type="PAKET_CORETAX",
            status="PASS",
            output_path="D:/output/coretax",
            artifact_count=8,
            validator_status="PASS",
            reconciliation_status="PASS",
            sha256="abc123",
            message="source reconciled",
        )
    )

    assert record_id > 0
    rows = service.list_for_wp("6101015612710001", 2025)
    assert len(rows) == 1
    row = rows[0]
    assert row["revision"] == 5
    assert row["export_type"] == "PAKET_CORETAX"
    assert row["status"] == "PASS"
    assert row["validator_status"] == "PASS"
    assert row["reconciliation_status"] == "PASS"
    assert row["artifact_count"] == 8


def test_export_audit_recent_is_newest_first(tmp_path):
    db_path = tmp_path / "audit.db"
    init_database(db_path)
    service = ExportAuditService(db_path=db_path)

    service.record(
        ExportAuditRecord(
            npwp="1",
            nama_wp="WP A",
            tahun_pajak=2025,
            revision=1,
            export_type="FORMAT_LAMA_PDF",
            status="PASS",
        )
    )
    service.record(
        ExportAuditRecord(
            npwp="2",
            nama_wp="WP B",
            tahun_pajak=2025,
            revision=2,
            export_type="PAKET_CORETAX",
            status="FAIL",
        )
    )

    rows = service.list_recent(limit=2)
    assert [row["npwp"] for row in rows] == ["2", "1"]
