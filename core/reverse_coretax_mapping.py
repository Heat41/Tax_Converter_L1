from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from config.constants import KategoriL1
from core.legacy_mapping import CORETAX_TO_EFORM
from config.database import get_db_connection


CATEGORY_ORDER = (
    KategoriL1.KAS.value,
    KategoriL1.PIUTANG.value,
    KategoriL1.INVESTASI.value,
    KategoriL1.BERGERAK.value,
    KategoriL1.HTB.value,
    KategoriL1.LAINNYA.value,
)


@dataclass(frozen=True)
class ReverseCoretaxIssue:
    code: str
    severity: str
    message: str
    row_number: Optional[int] = None


@dataclass(frozen=True)
class ReverseCoretaxRow:
    nomor: int
    kategori: str
    kode_harta: str
    nama_harta: str
    tahun_perolehan: int
    nilai: float
    nomor_akun_keterangan: str
    atas_nama: str
    nama_bank: str
    source_eform_code: str = ""
    official_metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class ReverseCoretaxPackage:
    npwp: str = ""
    nama_wp: str = ""
    tahun_pajak: int = 0
    revision: int = 0
    snapshot_hash: str = ""
    rows_by_category: Dict[str, List[ReverseCoretaxRow]] = field(
        default_factory=lambda: {key: [] for key in CATEGORY_ORDER}
    )
    issues: List[ReverseCoretaxIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ReverseCoretaxIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[ReverseCoretaxIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def can_export(self) -> bool:
        return not self.errors and any(self.rows_by_category.values())

    @property
    def total_rows(self) -> int:
        return sum(len(rows) for rows in self.rows_by_category.values())


class ReverseCoretaxMappingService:
    """Stage 8D.1 - mapping snapshot FINAL kembali ke kategori Coretax L-1 yang tersedia.

    Snapshot tetap mengenali enam kelompok schema L-1, tetapi hanya kategori yang
    benar-benar memiliki data yang diteruskan ke exporter. Tidak ada kategori
    kosong atau nilai yang dibuat-buat.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = db_path

    @staticmethod
    def _digits(value: object) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _category_from_code(code: str) -> Optional[str]:
        prefix = str(code or "")[:2]
        if prefix == "01":
            return KategoriL1.KAS.value
        if prefix == "02":
            return KategoriL1.PIUTANG.value
        if prefix == "03":
            return KategoriL1.INVESTASI.value
        if prefix == "04":
            return KategoriL1.BERGERAK.value
        if prefix == "05":
            return KategoriL1.HTB.value
        if prefix in {"06", "07"}:
            return KategoriL1.LAINNYA.value
        return None

    @staticmethod
    def _reverse_eform_candidates(kode_eform: str) -> List[str]:
        target = str(kode_eform or "").strip()
        return [
            code
            for code, eform in CORETAX_TO_EFORM.items()
            if eform == target
        ]

    def _resolve_coretax_code(
        self,
        item: dict,
        row_number: int,
        issues: List[ReverseCoretaxIssue],
    ) -> Optional[str]:
        kode_ct = str(item.get("kode_ct") or "").strip()
        if kode_ct:
            return kode_ct

        kode_eform = str(item.get("kode_eform") or "").strip()
        candidates = self._reverse_eform_candidates(kode_eform)
        if len(candidates) == 1:
            return candidates[0]

        if not candidates:
            issues.append(
                ReverseCoretaxIssue(
                    "RCT_103",
                    "ERROR",
                    f"Kode EFORM {kode_eform or '-'} tidak memiliki pasangan Coretax.",
                    row_number,
                )
            )
            return None

        issues.append(
            ReverseCoretaxIssue(
                "RCT_104",
                "ERROR",
                f"Kode EFORM {kode_eform} memiliki lebih dari satu pasangan Coretax "
                f"({', '.join(candidates)}). Kode CT asli wajib tersedia agar tidak menebak.",
                row_number,
            )
        )
        return None

    def build_active_final(self, npwp: str, tahun_pajak: int) -> ReverseCoretaxPackage:
        clean_npwp = self._digits(npwp)
        package = ReverseCoretaxPackage(
            npwp=clean_npwp,
            tahun_pajak=int(tahun_pajak or 0),
        )

        if not clean_npwp or not tahun_pajak:
            package.issues.append(
                ReverseCoretaxIssue(
                    "RCT_001",
                    "ERROR",
                    "NPWP dan Tahun Pajak wajib tersedia.",
                )
            )
            return package

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
                (clean_npwp, int(tahun_pajak)),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            package.issues.append(
                ReverseCoretaxIssue(
                    "RCT_002",
                    "ERROR",
                    "Snapshot FINAL belum tersedia.",
                )
            )
            return package

        package.nama_wp = str(row["nama_wp"] or "")
        package.revision = int(row["revision"] or 0)
        package.snapshot_hash = str(row["snapshot_hash"] or "")

        try:
            payload = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            package.issues.append(
                ReverseCoretaxIssue(
                    "RCT_003",
                    "ERROR",
                    "Snapshot FINAL rusak dan tidak dapat dibaca.",
                )
            )
            return package

        raw_rows = payload.get("harta_current_rows")
        if not isinstance(raw_rows, list) or not raw_rows:
            package.issues.append(
                ReverseCoretaxIssue(
                    "RCT_004",
                    "ERROR",
                    "Snapshot FINAL tidak memiliki Harta Current.",
                )
            )
            return package

        for index, item in enumerate(raw_rows, start=1):
            if not isinstance(item, dict):
                package.issues.append(
                    ReverseCoretaxIssue(
                        "RCT_101",
                        "ERROR",
                        "Struktur baris Harta FINAL tidak valid.",
                        index,
                    )
                )
                continue

            kode_ct = self._resolve_coretax_code(item, index, package.issues)
            if not kode_ct:
                continue

            category = self._category_from_code(kode_ct)
            if not category:
                package.issues.append(
                    ReverseCoretaxIssue(
                        "RCT_102",
                        "ERROR",
                        f"Kode Coretax {kode_ct} belum dapat dikelompokkan ke kategori L-1 yang dikenal.",
                        index,
                    )
                )
                continue

            try:
                year = int(float(item.get("tahun_perolehan") or 0))
                value = float(item.get("nilai_tahun_berjalan") or 0)
            except (TypeError, ValueError):
                package.issues.append(
                    ReverseCoretaxIssue(
                        "RCT_105",
                        "ERROR",
                        "Tahun perolehan atau nilai tahun berjalan tidak numerik.",
                        index,
                    )
                )
                continue

            package.rows_by_category[category].append(
                ReverseCoretaxRow(
                    nomor=len(package.rows_by_category[category]) + 1,
                    kategori=category,
                    kode_harta=kode_ct,
                    nama_harta=str(item.get("nama_harta") or "").strip(),
                    tahun_perolehan=year,
                    nilai=value,
                    nomor_akun_keterangan=str(
                        item.get("nomor_akun_keterangan") or ""
                    ).strip(),
                    atas_nama=str(item.get("atas_nama") or "").strip(),
                    nama_bank=str(item.get("nama_bank") or "").strip(),
                    source_eform_code=str(item.get("kode_eform") or "").strip(),
                    official_metadata=(
                        dict(item.get("coretax_metadata") or {})
                        if isinstance(item.get("coretax_metadata"), dict)
                        else {}
                    ),
                )
            )

        if package.total_rows and not package.errors:
            counts = ", ".join(
                f"{key}={len(package.rows_by_category[key])}"
                for key in CATEGORY_ORDER
            )
            package.issues.append(
                ReverseCoretaxIssue(
                    "RCT_INFO",
                    "INFO",
                    f"{package.total_rows} baris FINAL siap dipaketkan sesuai kategori data ({counts}).",
                )
            )

        return package
