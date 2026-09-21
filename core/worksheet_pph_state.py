from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from config.database import get_db_connection
from core.worksheet_sorting import sort_bupot_rows


@dataclass(frozen=True)
class WorksheetBupotRow:
    # Field inti / anchor mengikuti Rekap Bupot.
    jenis: str = ""
    no_bupot: str = ""
    bruto: float = 0.0
    pengurang: float = 0.0
    pph_dipotong: float = 0.0

    # Field pendukung mengikuti struktur Rekap Bupot Coretax.
    masa: str = ""
    tahun: str = ""
    sifat: str = ""
    status: str = ""
    npwp_penerima: str = ""
    nama_penerima: str = ""
    fasilitas: str = ""
    jenis_pph: str = ""
    kop: str = ""
    dpp_persen: float = 0.0
    tarif: float = 0.0
    bukti: str = ""
    no_bukti: str = ""
    tanggal_bukti: str = ""
    npwp_pemotong: str = ""
    nama_pemotong: str = ""
    tanggal_pemotongan: str = ""
    mekanisme_sp2d: str = ""
    no_sp2d: str = ""

    # Kompatibilitas dengan model lama / UI lama.
    npwp_pemberi_kerja: str = ""

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

        ordered_bupot_rows = sort_bupot_rows(bupot_rows)
        rows_json = json.dumps(
            [self._row_to_json(row) for row in ordered_bupot_rows],
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
                row_count=len(ordered_bupot_rows),
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _row_to_json(self, row: WorksheetBupotRow) -> dict:
        return {
            "jenis": row.jenis,
            "no_bupot": row.no_bupot,
            "bruto": float(row.bruto),
            "pengurang": float(row.pengurang),
            "pph_dipotong": float(row.pph_dipotong),
            "masa": row.masa,
            "tahun": row.tahun,
            "sifat": row.sifat,
            "status": row.status,
            "npwp_penerima": self.normalize_npwp(row.npwp_penerima),
            "nama_penerima": row.nama_penerima,
            "fasilitas": row.fasilitas,
            "jenis_pph": row.jenis_pph,
            "kop": row.kop,
            "dpp_persen": float(row.dpp_persen),
            "tarif": float(row.tarif),
            "bukti": row.bukti,
            "no_bukti": row.no_bukti,
            "tanggal_bukti": row.tanggal_bukti,
            "npwp_pemotong": self.normalize_npwp(row.npwp_pemotong),
            "nama_pemotong": row.nama_pemotong,
            "tanggal_pemotongan": row.tanggal_pemotongan,
            "mekanisme_sp2d": row.mekanisme_sp2d,
            "no_sp2d": row.no_sp2d,
            "npwp_pemberi_kerja": self.normalize_npwp(
                row.npwp_pemberi_kerja or row.npwp_pemotong
            ),
        }

    @staticmethod
    def _row_to_state(row) -> PersistedWorksheetPPhState:
        raw_rows = json.loads(row["bupot_rows_json"] or "[]")
        bupot_rows = [
            WorksheetBupotRow(
                jenis=str(item.get("jenis") or ""),
                no_bupot=str(item.get("no_bupot") or ""),
                bruto=float(item.get("bruto") or 0),
                pengurang=float(item.get("pengurang") or 0),
                pph_dipotong=float(item.get("pph_dipotong") or 0),
                masa=str(item.get("masa") or ""),
                tahun=str(item.get("tahun") or ""),
                sifat=str(item.get("sifat") or ""),
                status=str(item.get("status") or ""),
                npwp_penerima=str(item.get("npwp_penerima") or ""),
                nama_penerima=str(item.get("nama_penerima") or ""),
                fasilitas=str(item.get("fasilitas") or ""),
                jenis_pph=str(item.get("jenis_pph") or ""),
                kop=str(item.get("kop") or ""),
                dpp_persen=float(item.get("dpp_persen") or 0),
                tarif=float(item.get("tarif") or 0),
                bukti=str(item.get("bukti") or ""),
                no_bukti=str(item.get("no_bukti") or ""),
                tanggal_bukti=str(item.get("tanggal_bukti") or ""),
                npwp_pemotong=str(item.get("npwp_pemotong") or item.get("npwp_pemberi_kerja") or ""),
                nama_pemotong=str(item.get("nama_pemotong") or ""),
                tanggal_pemotongan=str(item.get("tanggal_pemotongan") or ""),
                mekanisme_sp2d=str(item.get("mekanisme_sp2d") or ""),
                no_sp2d=str(item.get("no_sp2d") or ""),
                npwp_pemberi_kerja=str(item.get("npwp_pemberi_kerja") or item.get("npwp_pemotong") or ""),
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
