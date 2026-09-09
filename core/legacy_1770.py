from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.database import get_db_connection
from core.legacy_mapping import LegacyFormatMappingService, LegacyHartaRow, LegacyMappingIssue


@dataclass(frozen=True)
class Legacy1770BupotRow:
    nomor: int
    jenis: str
    npwp_pemotong: str
    no_bupot: str
    bruto: float
    pengurang: float
    netto: float
    nama_pemotong: str = ""
    tanggal_bupot: str = ""
    pph_dipotong: float = 0.0


@dataclass(frozen=True)
class Legacy1770FinalIncomeRow:
    keterangan: str
    dpp: float
    tarif: float
    pph: float


@dataclass
class Legacy1770Document:
    npwp: str = ""
    nama_wp: str = ""
    tahun_pajak: int = 0
    revision: int = 0
    snapshot_hash: str = ""

    status_ptkp: str = ""
    total_netto_bupot: float = 0.0
    penghasilan_neto_lainnya: float = 0.0
    zakat: float = 0.0
    penghasilan_neto_gabungan: float = 0.0
    ptkp: float = 0.0
    pkp: float = 0.0
    pph_terutang: float = 0.0
    kredit_pajak: float = 0.0
    pph25: float = 0.0
    kurang_lebih_bayar: float = 0.0

    umkm_bruto: float = 0.0
    umkm_pph_setor: float = 0.0
    penghasilan_final_lainnya: List[Legacy1770FinalIncomeRow] = field(default_factory=list)
    penghasilan_bukan_objek: float = 0.0

    bupot_rows: List[Legacy1770BupotRow] = field(default_factory=list)
    harta_rows: List[LegacyHartaRow] = field(default_factory=list)
    issues: List[LegacyMappingIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LegacyMappingIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> List[LegacyMappingIssue]:
        return [issue for issue in self.issues if issue.severity == "WARNING"]

    @property
    def can_export_pdf(self) -> bool:
        return bool(self.npwp and self.nama_wp and self.tahun_pajak and not self.errors)


class Legacy1770DocumentService:
    """Stage 8C.1: bentuk model dokumen 1770 lama dari snapshot FINAL.

    Model ini mengikuti struktur 5 halaman acuan Lisa tanpa mengarang data yang
    belum dimiliki aplikasi. Field yang belum tersedia diberi warning dan tetap
    kosong pada renderer PDF.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path
        self.harta_mapper = LegacyFormatMappingService(db_path=db_path)

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def build_active_final(self, npwp: str, tahun_pajak: int) -> Legacy1770Document:
        clean_npwp = "".join(ch for ch in str(npwp or "") if ch.isdigit())
        document = Legacy1770Document(npwp=clean_npwp, tahun_pajak=int(tahun_pajak or 0))

        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT npwp, nama_wp, tahun_pajak, revision, snapshot_hash, snapshot_json
                FROM worksheet_final_snapshots
                WHERE npwp = ? AND tahun_pajak = ? AND status = 'FINAL'
                ORDER BY revision DESC
                LIMIT 1
                """,
                (clean_npwp, int(tahun_pajak or 0)),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            document.issues.append(
                LegacyMappingIssue(
                    "PDF_001", "ERROR", "Snapshot FINAL belum tersedia untuk membuat PDF Format Lama."
                )
            )
            return document

        document.nama_wp = str(row["nama_wp"] or "")
        document.tahun_pajak = int(row["tahun_pajak"] or 0)
        document.revision = int(row["revision"] or 0)
        document.snapshot_hash = str(row["snapshot_hash"] or "")

        try:
            payload: Dict[str, Any] = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            document.issues.append(
                LegacyMappingIssue("PDF_002", "ERROR", "Snapshot FINAL rusak dan tidak dapat dibaca.")
            )
            return document

        pph = payload.get("pph_calc_result") or {}
        components = payload.get("pph_components") or {}
        other = payload.get("penghasilan_lainnya") or {}
        umkm = payload.get("umkm_state") or {}

        document.status_ptkp = str(payload.get("status_ptkp") or components.get("status_ptkp") or "")
        document.total_netto_bupot = self._float(pph.get("total_netto_bupot"))
        document.penghasilan_neto_lainnya = self._float(pph.get("penghasilan_neto_lainnya"))
        document.zakat = self._float(payload.get("zakat", pph.get("pengurang_penghasilan_neto")))
        document.penghasilan_neto_gabungan = self._float(pph.get("penghasilan_neto_gabungan"))
        document.ptkp = self._float(pph.get("ptkp"))
        document.pkp = self._float(pph.get("pkp"))
        document.pph_terutang = self._float(pph.get("pph_terutang"))
        document.kredit_pajak = self._float(pph.get("kredit_pajak"))
        document.pph25 = self._float(pph.get("pph25"))
        document.kurang_lebih_bayar = self._float(
            pph.get("kurang_lebih_bayar_pembulatan", pph.get("kurang_lebih_bayar"))
        )

        document.umkm_bruto = sum(self._float(v) for v in (umkm.get("bruto_bulanan") or []))
        document.umkm_pph_setor = sum(self._float(v) for v in (umkm.get("pph_setor_bulanan") or []))

        final_rows = other.get("final_other_rows") or []
        for item in final_rows:
            if not isinstance(item, dict):
                continue
            dpp = self._float(item.get("dpp"))
            tarif = self._float(item.get("tarif"))
            document.penghasilan_final_lainnya.append(
                Legacy1770FinalIncomeRow(
                    keterangan=str(item.get("keterangan") or ""),
                    dpp=dpp,
                    tarif=tarif,
                    pph=round(dpp * tarif),
                )
            )

        document.penghasilan_bukan_objek = self._float(other.get("prive_dpp")) + self._float(
            other.get("hibah_warisan_dpp")
        )

        raw_bupot = payload.get("bupot_rows") or []
        for index, item in enumerate(raw_bupot, start=1):
            if not isinstance(item, dict):
                continue
            bruto = self._float(item.get("bruto"))
            pengurang = self._float(item.get("pengurang"))
            document.bupot_rows.append(
                Legacy1770BupotRow(
                    nomor=index,
                    jenis=str(item.get("jenis") or ""),
                    npwp_pemotong=str(item.get("npwp_pemberi_kerja") or ""),
                    no_bupot=str(item.get("no_bupot") or ""),
                    bruto=bruto,
                    pengurang=pengurang,
                    netto=bruto - pengurang,
                )
            )

        harta_result = self.harta_mapper.map_active_final(clean_npwp, document.tahun_pajak)
        document.harta_rows = list(harta_result.rows)
        document.issues.extend(harta_result.issues)

        if document.bupot_rows:
            document.issues.append(
                LegacyMappingIssue(
                    "PDF_W01",
                    "WARNING",
                    "Data Bupot saat ini belum menyimpan Nama Pemotong, Tanggal Bupot, dan PPh Dipotong; kolom tersebut akan kosong pada Lampiran II sampai field Worksheet ditambah.",
                )
            )

        document.issues.append(
            LegacyMappingIssue(
                "PDF_W02",
                "WARNING",
                "Data Utang dan Susunan Anggota Keluarga belum memiliki modul lengkap; Bagian B dan C Lampiran IV akan dibiarkan kosong.",
            )
        )

        return document
