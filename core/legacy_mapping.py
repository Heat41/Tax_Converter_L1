from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config.database import get_db_connection


CORETAX_TO_EFORM = {
    "0101": "011",
    "0102": "012",
    "0103": "013",
    "0104": "014",
    "0712": "019",
    "0799": "019",
    "0201": "021",
    "0202": "022",
    "0209": "029",
    "0301": "031",
    "0302": "032",
    "0304": "033",
    "0305": "034",
    "0306": "035",
    "0307": "036",
    "0308": "037",
    "0309": "038",
    "0399": "039",
    "0401": "041",
    "0402": "042",
    "0403": "043",
    "0499": "049",
    "0701": "051",
    "0702": "051",
    "0705": "052",
    "0706": "053",
    "0707": "054",
    "0708": "055",
    "0709": "055",
    "0501": "061",
    "0502": "061",
    "0506": "062",
    "0505": "063",
    "0509": "069",
    "0601": "071",
    "0602": "072",
    "0603": "073",
    "0699": "079",
}

VALID_EFORM_CODES = set(CORETAX_TO_EFORM.values())


@dataclass(frozen=True)
class LegacyMappingIssue:
    code: str
    severity: str
    message: str
    row_number: Optional[int] = None


@dataclass(frozen=True)
class LegacyHartaRow:
    nomor: int
    kode_eform: str
    kode_coretax: str
    kategori: str
    nama_harta: str
    nomor_akun_keterangan: str
    atas_nama: str
    nama_bank: str
    tahun_perolehan: int
    nilai_tahun_sebelumnya: float
    nilai_tahun_berjalan: float
    keterangan: str


@dataclass
class LegacyMappingResult:
    npwp: str = ""
    nama_wp: str = ""
    tahun_pajak: int = 0
    revision: int = 0
    snapshot_hash: str = ""
    rows: List[LegacyHartaRow] = field(default_factory=list)
    issues: List[LegacyMappingIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LegacyMappingIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> List[LegacyMappingIssue]:
        return [issue for issue in self.issues if issue.severity == "WARNING"]

    @property
    def can_export(self) -> bool:
        return not self.errors and bool(self.rows)


class LegacyFormatMappingService:
    """Stage 8B: map snapshot FINAL ke model netral Format Lama.

    Service ini belum membuat file Excel. Stage 8C akan mengikat model ini ke
    template/output fisik. Sumber data wajib snapshot FINAL agar hasil mapping
    tidak berubah mengikuti draft Worksheet setelah finalisasi.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path

    @staticmethod
    def map_coretax_code(kode_ct: object) -> Optional[str]:
        return CORETAX_TO_EFORM.get(str(kode_ct or "").strip())

    @staticmethod
    def category_from_eform(kode_eform: str) -> str:
        prefix = str(kode_eform or "")[:2]
        if prefix == "01":
            return "KAS"
        if prefix == "02":
            return "PIUTANG"
        if prefix == "03":
            return "INVESTASI"
        if prefix in {"04", "05"}:
            return "BERGERAK"
        if prefix == "06":
            return "HTB"
        if prefix == "07":
            return "LAINNYA"
        return "TIDAK_DIKENAL"

    def map_active_final(self, npwp: str, tahun_pajak: int) -> LegacyMappingResult:
        clean_npwp = "".join(ch for ch in str(npwp or "") if ch.isdigit())
        result = LegacyMappingResult(npwp=clean_npwp, tahun_pajak=int(tahun_pajak or 0))

        if not clean_npwp or not tahun_pajak:
            result.issues.append(
                LegacyMappingIssue(
                    "LGC_001",
                    "ERROR",
                    "NPWP dan Tahun Pajak wajib tersedia untuk mapping Format Lama.",
                )
            )
            return result

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
            result.issues.append(
                LegacyMappingIssue(
                    "LGC_002",
                    "ERROR",
                    "Snapshot FINAL belum tersedia. Finalisasi Worksheet terlebih dahulu.",
                )
            )
            return result

        result.nama_wp = str(row["nama_wp"] or "")
        result.revision = int(row["revision"] or 0)
        result.snapshot_hash = str(row["snapshot_hash"] or "")

        try:
            payload = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            result.issues.append(
                LegacyMappingIssue(
                    "LGC_003",
                    "ERROR",
                    "Snapshot FINAL rusak dan tidak dapat dibaca.",
                )
            )
            return result

        harta_rows = payload.get("harta_current_rows")
        if not isinstance(harta_rows, list) or not harta_rows:
            result.issues.append(
                LegacyMappingIssue(
                    "LGC_004",
                    "ERROR",
                    "Snapshot FINAL tidak memiliki Harta Current.",
                )
            )
            return result

        for index, item in enumerate(harta_rows, start=1):
            if not isinstance(item, dict):
                result.issues.append(
                    LegacyMappingIssue(
                        "LGC_005",
                        "ERROR",
                        "Struktur baris Harta pada snapshot tidak valid.",
                        index,
                    )
                )
                continue

            mapped_row = self._map_row(index, item, result.issues)
            if mapped_row is not None:
                result.rows.append(mapped_row)

        if result.rows and not result.errors:
            result.issues.append(
                LegacyMappingIssue(
                    "LGC_INFO",
                    "INFO",
                    f"{len(result.rows)} baris Harta berhasil dipetakan ke struktur Format Lama.",
                )
            )

        return result

    def _map_row(
        self,
        row_number: int,
        item: dict,
        issues: List[LegacyMappingIssue],
    ) -> Optional[LegacyHartaRow]:
        kode_ct = str(item.get("kode_ct") or "").strip()
        provided_eform = str(item.get("kode_eform") or "").strip()
        derived_eform = self.map_coretax_code(kode_ct)

        if provided_eform:
            if provided_eform not in VALID_EFORM_CODES:
                issues.append(
                    LegacyMappingIssue(
                        "LGC_101",
                        "ERROR",
                        f"Kode EFORM {provided_eform} tidak dikenal.",
                        row_number,
                    )
                )
                return None
            kode_eform = provided_eform
            if derived_eform and derived_eform != provided_eform:
                issues.append(
                    LegacyMappingIssue(
                        "LGC_102",
                        "WARNING",
                        f"Kode EFORM manual {provided_eform} berbeda dari mapping Coretax {kode_ct} → {derived_eform}; nilai manual dipertahankan.",
                        row_number,
                    )
                )
        else:
            if not derived_eform:
                issues.append(
                    LegacyMappingIssue(
                        "LGC_103",
                        "ERROR",
                        f"Kode Coretax {kode_ct or '-'} belum memiliki mapping ke EFORM.",
                        row_number,
                    )
                )
                return None
            kode_eform = derived_eform

        try:
            tahun = int(float(item.get("tahun_perolehan") or 0))
            previous = float(item.get("nilai_tahun_sebelumnya") or 0)
            current = float(item.get("nilai_tahun_berjalan") or 0)
        except (TypeError, ValueError):
            issues.append(
                LegacyMappingIssue(
                    "LGC_104",
                    "ERROR",
                    "Tahun perolehan atau nilai Harta tidak numerik.",
                    row_number,
                )
            )
            return None

        description_parts = [
            str(item.get("nomor_akun_keterangan") or "").strip(),
            str(item.get("atas_nama") or "").strip(),
            str(item.get("nama_bank") or "").strip(),
        ]
        keterangan = "; ".join(
            value for value in description_parts if value and value != "-"
        )

        return LegacyHartaRow(
            nomor=int(item.get("nomor") or row_number),
            kode_eform=kode_eform,
            kode_coretax=kode_ct,
            kategori=self.category_from_eform(kode_eform),
            nama_harta=str(item.get("nama_harta") or "").strip(),
            nomor_akun_keterangan=str(item.get("nomor_akun_keterangan") or "").strip(),
            atas_nama=str(item.get("atas_nama") or "").strip(),
            nama_bank=str(item.get("nama_bank") or "").strip(),
            tahun_perolehan=tahun,
            nilai_tahun_sebelumnya=previous,
            nilai_tahun_berjalan=current,
            keterangan=keterangan,
        )
