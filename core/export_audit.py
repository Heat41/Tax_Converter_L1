from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from config.database import get_db_connection


@dataclass(frozen=True)
class ExportAuditRecord:
    npwp: str
    nama_wp: str
    tahun_pajak: int
    revision: int
    export_type: str
    status: str
    output_path: str = ""
    artifact_count: int = 0
    validator_status: str = ""
    reconciliation_status: str = ""
    sha256: str = ""
    message: str = ""


class ExportAuditService:
    """Stage 8D.4M - simpan dan baca jejak export final."""

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = db_path

    def record(self, item: ExportAuditRecord) -> int:
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute(
                """
                INSERT INTO export_audit_log (
                    npwp, nama_wp, tahun_pajak, revision,
                    export_type, status, output_path, artifact_count,
                    validator_status, reconciliation_status,
                    sha256, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.npwp,
                    item.nama_wp,
                    int(item.tahun_pajak),
                    int(item.revision),
                    item.export_type,
                    item.status,
                    item.output_path,
                    int(item.artifact_count),
                    item.validator_status,
                    item.reconciliation_status,
                    item.sha256,
                    item.message,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_for_wp(
        self,
        npwp: str,
        tahun_pajak: int,
        *,
        limit: int = 50,
    ) -> List[object]:
        conn = get_db_connection(self.db_path)
        try:
            return conn.execute(
                """
                SELECT *
                FROM export_audit_log
                WHERE npwp = ? AND tahun_pajak = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(npwp), int(tahun_pajak), int(limit)),
            ).fetchall()
        finally:
            conn.close()

    def list_recent(self, *, limit: int = 8) -> List[object]:
        conn = get_db_connection(self.db_path)
        try:
            return conn.execute(
                """
                SELECT *
                FROM export_audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        finally:
            conn.close()
