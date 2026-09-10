from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from config.database import get_db_connection


@dataclass(frozen=True)
class WorksheetBupotRow:
    jenis: str = ""
    npwp_pemberi_kerja: str = ""
    no_bupot: str = ""
    bruto: float = 0.0
    pengurang: float = 0.0
    pph_dipotong: float = 0.0

    @property
    def netto(self) -> float:
        return float(self.bruto) - float(self.pengurang)


@dataclass
class PersistedWorksheetPPhState:
    id: int
    npwp: str
    tahun_pajak: int
    bupot_rows: List[WorksheetBupotRow]
    components: dict
    updated_at: Optional[str] = None


@dataclass
class WorksheetPPhSaveResult:
    state_id: int
    row_count: int
    persisted: bool = True


class WorksheetPPhStateStore:
    """Persistence Worksheet Penghasilan & PPh per NPWP + Tahun Pajak."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path

    @staticmethod
    def normalize_npwp(value: object) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    def load(self, npwp: str, tahun_pajak: int) -> Optional[PersistedWorksheetPPhState]:
        clean_npwp = self.normalize_npwp(npwp)
        if not clean_npwp:
            return None

        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT *
                FROM worksheet_pph_states
                WHERE npwp = ? AND tahun_pajak = ?
                LIMIT 1
                """,
                (clean_npwp, int(tahun_pajak)),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_state(row)
        finally:
            conn.close()

    def save(
        self,
        *,
        npwp: str,
        tahun_pajak: int,
        bupot_rows: List[WorksheetBupotRow],
        components: Optional[dict] = None,
    ) -> WorksheetPPhSaveResult:
        clean_npwp = self.normalize_npwp(npwp)
        if not clean_npwp:
            raise ValueError("NPWP WP tidak tersedia untuk menyimpan Worksheet PPh.")

        rows_json = json.dumps(
            [
                {
                    "jenis": row.jenis,
                    "npwp_pemberi_kerja": self.normalize_npwp(row.npwp_pemberi_kerja),
                    "no_bupot": row.no_bupot,
                    "bruto": float(row.bruto),
                    "pengurang": float(row.pengurang),
                    "pph_dipotong": float(getattr(row, "pph_dipotong", 0.0) or 0.0),
                }
                for row in bupot_rows
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        components_json = json.dumps(components or {}, ensure_ascii=False, separators=(",", ":"))

        conn = get_db_connection(self.db_path)
        try:
            existing = conn.execute(
                """
                SELECT id
                FROM worksheet_pph_states
                WHERE npwp = ? AND tahun_pajak = ?
                LIMIT 1
                """,
                (clean_npwp, int(tahun_pajak)),
            ).fetchone()

            if existing is None:
                cursor = conn.execute(
                    """
                    INSERT INTO worksheet_pph_states (
                        npwp, tahun_pajak, bupot_rows_json, components_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (clean_npwp, int(tahun_pajak), rows_json, components_json),
                )
                state_id = int(cursor.lastrowid)
            else:
                state_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE worksheet_pph_states
                    SET bupot_rows_json = ?,
                        components_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (rows_json, components_json, state_id),
                )

            conn.commit()
            return WorksheetPPhSaveResult(
                state_id=state_id,
                row_count=len(bupot_rows),
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _row_to_state(row) -> PersistedWorksheetPPhState:
        raw_rows = json.loads(row["bupot_rows_json"] or "[]")
        bupot_rows = [
            WorksheetBupotRow(
                jenis=str(item.get("jenis") or ""),
                npwp_pemberi_kerja=str(item.get("npwp_pemberi_kerja") or ""),
                no_bupot=str(item.get("no_bupot") or ""),
                bruto=float(item.get("bruto") or 0),
                pengurang=float(item.get("pengurang") or 0),
                pph_dipotong=float(item.get("pph_dipotong") or 0),
            )
            for item in raw_rows
        ]
        return PersistedWorksheetPPhState(
            id=int(row["id"]),
            npwp=row["npwp"],
            tahun_pajak=int(row["tahun_pajak"]),
            bupot_rows=bupot_rows,
            components=json.loads(row["components_json"] or "{}"),
            updated_at=row["updated_at"],
        )