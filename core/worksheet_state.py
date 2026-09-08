from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from config.database import get_db_connection
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow


@dataclass
class PersistedWorksheetHartaState:
    id: int
    npwp: str
    tahun_pajak: int
    original_hash: str
    original_rows: List[WorksheetHartaRow]
    current_rows: List[WorksheetHartaRow]
    origin_indices: List[Optional[int]]
    updated_at: Optional[str] = None


@dataclass
class WorksheetSaveResult:
    state_id: int
    audit_count: int
    add_count: int
    edit_count: int
    delete_count: int
    persisted: bool = True


@dataclass
class _AuditChange:
    action: str
    origin_index: Optional[int]
    row_order: Optional[int]
    nama_kolom: str
    nilai_lama: Optional[str]
    nilai_baru: Optional[str]


class WorksheetHartaStateStore:
    """Persistence untuk state Edited / Current pada Worksheet Harta.

    State disimpan per NPWP + Tahun Pajak + fingerprint Original Import. Dengan
    demikian draft dari baseline import yang berbeda tidak akan dipulihkan ke
    data baru secara diam-diam.
    """

    AUDIT_FIELDS = (
        "kode_eform",
        "kode_ct",
        "nama_harta",
        "nomor_akun_keterangan",
        "atas_nama",
        "nama_bank",
        "tahun_perolehan",
        "nilai_tahun_sebelumnya",
        "nilai_tahun_berjalan",
    )

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path

    @staticmethod
    def normalize_npwp(value: object) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @classmethod
    def original_hash(cls, rows: Iterable[WorksheetHartaRow]) -> str:
        payload = cls._rows_to_json(list(rows))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def load_matching(
        self,
        npwp: str,
        tahun_pajak: int,
        original_rows: Iterable[WorksheetHartaRow],
    ) -> Optional[PersistedWorksheetHartaState]:
        clean_npwp = self.normalize_npwp(npwp)
        rows = list(original_rows)
        if not clean_npwp or not rows:
            return None

        fingerprint = self.original_hash(rows)
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT *
                FROM worksheet_harta_states
                WHERE npwp = ? AND tahun_pajak = ? AND original_hash = ?
                LIMIT 1
                """,
                (clean_npwp, int(tahun_pajak), fingerprint),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_state(row)
        finally:
            conn.close()

    def save_state(
        self,
        *,
        npwp: str,
        tahun_pajak: int,
        original_rows: Iterable[WorksheetHartaRow],
        current_rows: Iterable[WorksheetHartaRow],
        origin_indices: Iterable[Optional[int]],
    ) -> WorksheetSaveResult:
        clean_npwp = self.normalize_npwp(npwp)
        if not clean_npwp:
            raise ValueError("NPWP tidak tersedia untuk menyimpan Worksheet Harta.")

        original = list(original_rows)
        current = list(current_rows)
        origins = list(origin_indices)
        if len(current) != len(origins):
            raise ValueError("Jumlah current_rows dan origin_indices tidak sama.")

        fingerprint = self.original_hash(original)
        conn = get_db_connection(self.db_path)
        try:
            existing_row = conn.execute(
                """
                SELECT *
                FROM worksheet_harta_states
                WHERE npwp = ? AND tahun_pajak = ? AND original_hash = ?
                LIMIT 1
                """,
                (clean_npwp, int(tahun_pajak), fingerprint),
            ).fetchone()

            if existing_row is not None:
                existing = self._row_to_state(existing_row)
                previous_rows = existing.current_rows
                previous_origins = existing.origin_indices
                state_id = existing.id
            else:
                previous_rows = list(original)
                previous_origins = list(range(len(original)))
                state_id = 0

            changes = self._diff(
                previous_rows,
                previous_origins,
                current,
                origins,
            )

            original_json = self._rows_to_json(original)
            current_json = self._rows_to_json(current)
            origins_json = json.dumps(origins, ensure_ascii=False)

            if existing_row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO worksheet_harta_states (
                        npwp,
                        tahun_pajak,
                        original_hash,
                        original_rows_json,
                        current_rows_json,
                        origin_indices_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean_npwp,
                        int(tahun_pajak),
                        fingerprint,
                        original_json,
                        current_json,
                        origins_json,
                    ),
                )
                state_id = int(cursor.lastrowid)
            else:
                conn.execute(
                    """
                    UPDATE worksheet_harta_states
                    SET current_rows_json = ?,
                        origin_indices_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (current_json, origins_json, state_id),
                )

            for change in changes:
                conn.execute(
                    """
                    INSERT INTO worksheet_harta_audit (
                        state_id,
                        action,
                        origin_index,
                        row_order,
                        nama_kolom,
                        nilai_lama,
                        nilai_baru
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state_id,
                        change.action,
                        change.origin_index,
                        change.row_order,
                        change.nama_kolom,
                        change.nilai_lama,
                        change.nilai_baru,
                    ),
                )

            conn.commit()

            add_count = sum(c.action == "ADD" for c in changes)
            edit_count = sum(c.action == "EDIT" for c in changes)
            delete_count = sum(c.action == "DELETE" for c in changes)
            return WorksheetSaveResult(
                state_id=state_id,
                audit_count=len(changes),
                add_count=add_count,
                edit_count=edit_count,
                delete_count=delete_count,
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_audit_rows(self, state_id: int):
        conn = get_db_connection(self.db_path)
        try:
            return conn.execute(
                """
                SELECT *
                FROM worksheet_harta_audit
                WHERE state_id = ?
                ORDER BY waktu_perubahan ASC, id ASC
                """,
                (state_id,),
            ).fetchall()
        finally:
            conn.close()

    @classmethod
    def _diff(
        cls,
        previous_rows: List[WorksheetHartaRow],
        previous_origins: List[Optional[int]],
        current_rows: List[WorksheetHartaRow],
        current_origins: List[Optional[int]],
    ) -> List[_AuditChange]:
        changes: List[_AuditChange] = []

        prev_original = {
            int(origin): (position, row)
            for position, (row, origin) in enumerate(
                zip(previous_rows, previous_origins)
            )
            if origin is not None
        }
        curr_original = {
            int(origin): (position, row)
            for position, (row, origin) in enumerate(
                zip(current_rows, current_origins)
            )
            if origin is not None
        }

        for origin in sorted(prev_original.keys() - curr_original.keys()):
            position, row = prev_original[origin]
            changes.append(
                _AuditChange(
                    action="DELETE",
                    origin_index=origin,
                    row_order=position + 1,
                    nama_kolom="__row__",
                    nilai_lama=cls._row_to_json(row),
                    nilai_baru=None,
                )
            )

        for origin in sorted(curr_original.keys() - prev_original.keys()):
            position, row = curr_original[origin]
            changes.append(
                _AuditChange(
                    action="ADD",
                    origin_index=origin,
                    row_order=position + 1,
                    nama_kolom="__row__",
                    nilai_lama=None,
                    nilai_baru=cls._row_to_json(row),
                )
            )

        for origin in sorted(prev_original.keys() & curr_original.keys()):
            _, old_row = prev_original[origin]
            new_position, new_row = curr_original[origin]
            changes.extend(
                cls._diff_row_fields(
                    old_row,
                    new_row,
                    origin_index=origin,
                    row_order=new_position + 1,
                )
            )

        prev_manual = [
            (position, row)
            for position, (row, origin) in enumerate(
                zip(previous_rows, previous_origins)
            )
            if origin is None
        ]
        curr_manual = [
            (position, row)
            for position, (row, origin) in enumerate(
                zip(current_rows, current_origins)
            )
            if origin is None
        ]

        common_manual = min(len(prev_manual), len(curr_manual))
        for index in range(common_manual):
            _, old_row = prev_manual[index]
            new_position, new_row = curr_manual[index]
            changes.extend(
                cls._diff_row_fields(
                    old_row,
                    new_row,
                    origin_index=None,
                    row_order=new_position + 1,
                )
            )

        for position, row in curr_manual[common_manual:]:
            changes.append(
                _AuditChange(
                    action="ADD",
                    origin_index=None,
                    row_order=position + 1,
                    nama_kolom="__row__",
                    nilai_lama=None,
                    nilai_baru=cls._row_to_json(row),
                )
            )

        for position, row in prev_manual[common_manual:]:
            changes.append(
                _AuditChange(
                    action="DELETE",
                    origin_index=None,
                    row_order=position + 1,
                    nama_kolom="__row__",
                    nilai_lama=cls._row_to_json(row),
                    nilai_baru=None,
                )
            )

        return changes

    @classmethod
    def _diff_row_fields(
        cls,
        old_row: WorksheetHartaRow,
        new_row: WorksheetHartaRow,
        *,
        origin_index: Optional[int],
        row_order: int,
    ) -> List[_AuditChange]:
        changes: List[_AuditChange] = []
        for field_name in cls.AUDIT_FIELDS:
            old_value = getattr(old_row, field_name)
            new_value = getattr(new_row, field_name)
            if old_value == new_value:
                continue
            changes.append(
                _AuditChange(
                    action="EDIT",
                    origin_index=origin_index,
                    row_order=row_order,
                    nama_kolom=field_name,
                    nilai_lama=cls._text(old_value),
                    nilai_baru=cls._text(new_value),
                )
            )
        return changes

    @staticmethod
    def _text(value: object) -> Optional[str]:
        return None if value is None else str(value)

    @staticmethod
    def _row_to_json(row: WorksheetHartaRow) -> str:
        return json.dumps(asdict(row), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _rows_to_json(rows: List[WorksheetHartaRow]) -> str:
        return json.dumps(
            [asdict(row) for row in rows],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _rows_from_json(payload: str) -> List[WorksheetHartaRow]:
        data = json.loads(payload or "[]")
        return [WorksheetHartaRow(**item) for item in data]

    @classmethod
    def _row_to_state(cls, row) -> PersistedWorksheetHartaState:
        current_rows = cls._rows_from_json(row["current_rows_json"])
        origin_indices = json.loads(row["origin_indices_json"] or "[]")
        if len(current_rows) != len(origin_indices):
            raise ValueError("State Worksheet Harta di database tidak konsisten.")
        return PersistedWorksheetHartaState(
            id=int(row["id"]),
            npwp=row["npwp"],
            tahun_pajak=int(row["tahun_pajak"]),
            original_hash=row["original_hash"],
            original_rows=cls._rows_from_json(row["original_rows_json"]),
            current_rows=current_rows,
            origin_indices=origin_indices,
            updated_at=row["updated_at"],
        )
