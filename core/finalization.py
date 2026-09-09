import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.database import get_db_connection
from core.evy_reconciliation import EvyReconciliationResult
from core.worksheet_pph_state import WorksheetBupotRow
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None


@dataclass
class FinalizationValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    @property
    def can_finalize(self) -> bool:
        return len(self.errors) == 0


@dataclass
class FinalizationInput:
    npwp: str
    nama_wp: str
    tahun_pajak: int
    harta_current_rows: List[WorksheetHartaRow]
    harta_original_hash: str
    bupot_rows: List[WorksheetBupotRow]
    pph_components: Dict[str, Any]
    umkm_state: Dict[str, Any]
    penghasilan_lainnya: Dict[str, Any]
    zakat: float
    status_ptkp: str
    pph_calc_result: Dict[str, Any]
    analisis_result: EvyReconciliationResult
    is_harta_dirty: bool = False
    is_pph_dirty: bool = False
    is_analisis_dirty: bool = False


@dataclass
class FinalSnapshotPayload:
    npwp: str
    nama_wp: str
    tahun_pajak: int
    harta_current_rows: List[Dict[str, Any]]
    harta_original_hash: str
    bupot_rows: List[Dict[str, Any]]
    pph_components: Dict[str, Any]
    umkm_state: Dict[str, Any]
    penghasilan_lainnya: Dict[str, Any]
    zakat: float
    status_ptkp: str
    pph_calc_result: Dict[str, Any]
    analisis_result: Dict[str, Any]
    timestamp: str


@dataclass
class FinalizationResult:
    success: bool
    snapshot_id: Optional[int]
    revision: Optional[int]
    snapshot_hash: Optional[str]
    validation_result: FinalizationValidationResult
    message: str = ""


class FinalizationService:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path

    def validate(self, data: FinalizationInput) -> FinalizationValidationResult:
        res = FinalizationValidationResult()

        # BLOCKING: Identitas
        if not data.npwp or len(str(data.npwp)) < 15:
            res.issues.append(ValidationIssue("ID_001", ValidationSeverity.ERROR, "NPWP kosong atau tidak valid", "npwp"))
        if not data.nama_wp:
            res.issues.append(ValidationIssue("ID_002", ValidationSeverity.ERROR, "Nama WP kosong", "nama_wp"))
        if not data.tahun_pajak or data.tahun_pajak < 2000:
            res.issues.append(ValidationIssue("ID_003", ValidationSeverity.ERROR, "Tahun Pajak invalid", "tahun_pajak"))

        # BLOCKING: Dirty states
        if data.is_harta_dirty:
            res.issues.append(ValidationIssue("DIRTY_001", ValidationSeverity.ERROR, "Perubahan Harta belum disimpan", "harta"))
        if data.is_pph_dirty:
            res.issues.append(ValidationIssue("DIRTY_002", ValidationSeverity.ERROR, "Perubahan PPh belum disimpan", "pph"))
        if data.is_analisis_dirty:
            res.issues.append(ValidationIssue("DIRTY_003", ValidationSeverity.ERROR, "Perubahan Analisis belum disimpan", "analisis"))

        # BLOCKING: Harta
        if not data.harta_current_rows:
            res.issues.append(ValidationIssue("HRT_001", ValidationSeverity.ERROR, "Harta Current tidak tersedia", "harta"))
        else:
            for row in data.harta_current_rows:
                if not row.kode_ct:
                    res.issues.append(ValidationIssue("HRT_002", ValidationSeverity.ERROR, f"Kode Harta kosong pada baris {row.nomor}", "kode_ct"))
                if not row.tahun_perolehan or row.tahun_perolehan < 1900 or row.tahun_perolehan > data.tahun_pajak:
                    res.issues.append(ValidationIssue("HRT_003", ValidationSeverity.ERROR, f"Tahun Perolehan invalid pada baris {row.nomor}", "tahun_perolehan"))
                try:
                    float(row.nilai_tahun_berjalan)
                    float(row.nilai_tahun_sebelumnya)
                except (ValueError, TypeError):
                    res.issues.append(ValidationIssue("HRT_004", ValidationSeverity.ERROR, f"Nilai numerik invalid pada baris {row.nomor}", "nilai_tahun_berjalan"))

        # BLOCKING: PPh state
        if not data.status_ptkp:
            res.issues.append(ValidationIssue("PPH_001", ValidationSeverity.ERROR, "Status PTKP kosong", "status_ptkp"))
        
        # Bupot validasi
        for idx, b in enumerate(data.bupot_rows):
            if b.bruto < 0 or b.pengurang < 0:
                res.issues.append(ValidationIssue("BPT_001", ValidationSeverity.ERROR, f"Nilai bruto/pengurang negatif pada bupot baris {idx+1}", "bupot"))

        # WARNINGS
        if data.analisis_result and abs(data.analisis_result.selisih_pengeluaran_vs_penghasilan) > 1.0:
            res.issues.append(ValidationIssue("ANL_001", ValidationSeverity.WARNING, "Rekonsiliasi tidak seimbang (Selisih bukan 0)", "rekonsiliasi"))

        # INFOS
        res.issues.append(ValidationIssue("INF_001", ValidationSeverity.INFO, f"Jumlah Harta: {len(data.harta_current_rows)} baris"))
        def safe_float(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0
                
        total_harta = sum(safe_float(r.nilai_tahun_berjalan) for r in data.harta_current_rows) if data.harta_current_rows else 0.0
        res.issues.append(ValidationIssue("INF_002", ValidationSeverity.INFO, f"Total Nilai Harta: {total_harta:,.2f}"))
        res.issues.append(ValidationIssue("INF_003", ValidationSeverity.INFO, f"Jumlah Bupot: {len(data.bupot_rows)} baris"))
        res.issues.append(ValidationIssue("INF_004", ValidationSeverity.INFO, f"Status PTKP: {data.status_ptkp}"))
        
        if data.analisis_result:
            res.issues.append(ValidationIssue("INF_005", ValidationSeverity.INFO, f"Penghasilan Netto: {data.analisis_result.penghasilan_netto:,.2f}"))
            res.issues.append(ValidationIssue("INF_006", ValidationSeverity.INFO, f"Total Pengeluaran: {data.analisis_result.total_pengeluaran:,.2f}"))

        return res

    def build_snapshot(self, data: FinalizationInput) -> tuple[str, str]:
        """Build canonical JSON payload and its SHA-256 hash."""
        payload = FinalSnapshotPayload(
            npwp=data.npwp,
            nama_wp=data.nama_wp,
            tahun_pajak=data.tahun_pajak,
            harta_current_rows=[asdict(r) for r in data.harta_current_rows],
            harta_original_hash=data.harta_original_hash,
            bupot_rows=[asdict(r) for r in data.bupot_rows],
            pph_components=data.pph_components,
            umkm_state=data.umkm_state,
            penghasilan_lainnya=data.penghasilan_lainnya,
            zakat=data.zakat,
            status_ptkp=data.status_ptkp,
            pph_calc_result=data.pph_calc_result,
            analisis_result=asdict(data.analisis_result) if data.analisis_result else {},
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        payload_dict = asdict(payload)
        # Hashing logic requires ignoring timestamp for deterministic hash of payload content
        # Or we hash including timestamp? Usually, snapshot hash includes content. 
        # But we'll include it. If we want same payload = same hash, we must exclude timestamp or fix it.
        # Let's create a hashable dict without the timestamp.
        hashable_dict = payload_dict.copy()
        hashable_dict.pop("timestamp", None)
        
        json_str = json.dumps(payload_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        hash_str = json.dumps(hashable_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        snapshot_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()
        
        return json_str, snapshot_hash

    def finalize(self, data: FinalizationInput) -> FinalizationResult:
        val_res = self.validate(data)
        if not val_res.can_finalize:
            return FinalizationResult(
                success=False,
                snapshot_id=None,
                revision=None,
                snapshot_hash=None,
                validation_result=val_res,
                message="Terdapat error blocking yang mencegah finalisasi."
            )

        snapshot_json, snapshot_hash = self.build_snapshot(data)
        val_json = json.dumps([asdict(i) for i in val_res.issues], ensure_ascii=False)

        conn = get_db_connection(self.db_path)
        try:
            # Check for existing active FINAL
            active_final = conn.execute(
                """
                SELECT id 
                FROM worksheet_final_snapshots 
                WHERE npwp = ? AND tahun_pajak = ? AND status = 'FINAL'
                """,
                (data.npwp, data.tahun_pajak)
            ).fetchone()
            
            if active_final:
                return FinalizationResult(
                    success=False,
                    snapshot_id=None,
                    revision=None,
                    snapshot_hash=None,
                    validation_result=val_res,
                    message="ACTIVE_FINAL_EXISTS: Terdapat finalisasi aktif. Harap batal finalisasi (VOID) terlebih dahulu."
                )

            # Determine next revision
            cursor = conn.execute(
                """
                SELECT MAX(revision) as max_rev 
                FROM worksheet_final_snapshots 
                WHERE npwp = ? AND tahun_pajak = ?
                """,
                (data.npwp, data.tahun_pajak)
            )
            row = cursor.fetchone()
            next_rev = (row["max_rev"] or 0) + 1

            # Insert new snapshot
            cur = conn.execute(
                """
                INSERT INTO worksheet_final_snapshots (
                    npwp, nama_wp, tahun_pajak, revision, status,
                    snapshot_schema_version, snapshot_json, validation_json, snapshot_hash
                ) VALUES (?, ?, ?, ?, 'FINAL', 1, ?, ?, ?)
                """,
                (data.npwp, data.nama_wp, data.tahun_pajak, next_rev, snapshot_json, val_json, snapshot_hash)
            )
            snapshot_id = cur.lastrowid
            
            # Since we allow multiple FINAL per NPWP+Year according to the prompt:
            # "Jangan otomatis VOID snapshot lama saat finalize biasa kecuali desain memang membutuhkan satu active FINAL."
            # We'll just leave previous FINAL alone, or UI can manage it.
            
            conn.commit()
            return FinalizationResult(
                success=True,
                snapshot_id=snapshot_id,
                revision=next_rev,
                snapshot_hash=snapshot_hash,
                validation_result=val_res,
                message="Finalisasi berhasil disimpan."
            )
        except Exception as e:
            conn.rollback()
            return FinalizationResult(
                success=False,
                snapshot_id=None,
                revision=None,
                snapshot_hash=None,
                validation_result=val_res,
                message=f"Database error: {str(e)}"
            )
        finally:
            conn.close()

    def void_snapshot(self, snapshot_id: int, reason: str) -> bool:
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute("SELECT status FROM worksheet_final_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            if not row or row["status"] != "FINAL":
                return False

            conn.execute(
                """
                UPDATE worksheet_final_snapshots 
                SET status = 'VOID', voided_at = CURRENT_TIMESTAMP, void_reason = ? 
                WHERE id = ?
                """,
                (reason, snapshot_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
