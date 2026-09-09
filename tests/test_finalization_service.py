import json
import sqlite3
import pytest
from unittest.mock import patch
from dataclasses import replace

from config.database import init_database, get_db_connection
from core.finalization import (
    FinalizationService, 
    FinalizationInput, 
    ValidationSeverity
)
from core.worksheet_pph_state import WorksheetBupotRow
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.evy_reconciliation import EvyReconciliationResult

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    init_database(db_file)
    yield db_file

@pytest.fixture
def valid_input():
    harta_rows = [
        WorksheetHartaRow(
            nomor=1,
            kode_eform="011",
            kode_ct="011",
            nama_harta="Uang Tunai",
            nomor_akun_keterangan="-",
            atas_nama="Wajib Pajak",
            nama_bank="-",
            tahun_perolehan=2020,
            nilai_tahun_sebelumnya=10000000.0,
            nilai_tahun_berjalan=15000000.0,
        )
    ]
    bupot_rows = [
        WorksheetBupotRow(
            jenis="Pekerjaan",
            npwp_pemberi_kerja="123456789012345",
            no_bupot="123",
            bruto=100000000.0,
            pengurang=5000000.0,
        )
    ]
    analisis = EvyReconciliationResult(
        total_harta_sebelumnya=10000000.0,
        total_harta_berjalan=15000000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=5000000.0,
        biaya_hidup_setahun=19200000.0,
        pajak_pajak=0.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=24200000.0,
        penghasilan_bruto_umkm=0.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=0.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=24200000.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )
    return FinalizationInput(
        npwp="1234567890123456",
        nama_wp="Budi",
        tahun_pajak=2025,
        harta_current_rows=harta_rows,
        harta_original_hash="abc123hash",
        bupot_rows=bupot_rows,
        pph_components={},
        umkm_state={},
        penghasilan_lainnya={},
        zakat=0.0,
        status_ptkp="TK/0",
        pph_calc_result={},
        analisis_result=analisis,
    )

def test_successful_finalization(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    result = service.finalize(valid_input)
    assert result.success is True
    assert result.snapshot_id is not None
    assert result.revision == 1
    assert result.snapshot_hash is not None

def test_second_finalize_blocked_while_active_final_exists(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    res1 = service.finalize(valid_input)
    assert res1.success is True
    
    res2 = service.finalize(valid_input)
    assert res2.success is False
    assert "ACTIVE_FINAL_EXISTS" in res2.message

def test_finalize_after_void_creates_next_revision(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    res1 = service.finalize(valid_input)
    assert res1.revision == 1
    
    service.void_snapshot(res1.snapshot_id, "Revisi 1")
    
    res2 = service.finalize(valid_input)
    assert res2.success is True
    assert res2.revision == 2

def test_revision_number_not_reused_after_void(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    res1 = service.finalize(valid_input)
    service.void_snapshot(res1.snapshot_id, "Voiding")
    
    res2 = service.finalize(valid_input)
    assert res2.revision == 2
    service.void_snapshot(res2.snapshot_id, "Voiding again")
    
    res3 = service.finalize(valid_input)
    assert res3.revision == 3

def test_structural_harta_current_vs_original(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    res = service.finalize(valid_input)
    
    conn = get_db_connection(temp_db)
    row = conn.execute("SELECT snapshot_json FROM worksheet_final_snapshots WHERE id=?", (res.snapshot_id,)).fetchone()
    conn.close()
    
    payload = json.loads(row["snapshot_json"])
    
    assert "harta_current_rows" in payload
    assert "original_rows" not in payload
    
    current_rows = payload["harta_current_rows"]
    assert len(current_rows) == 1
    assert current_rows[0]["nilai_tahun_berjalan"] == 15000000.0

def test_void_preserves_exactly_same_data_and_updates_metadata(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    res = service.finalize(valid_input)
    
    conn = get_db_connection(temp_db)
    before_row = conn.execute("SELECT * FROM worksheet_final_snapshots WHERE id=?", (res.snapshot_id,)).fetchone()
    before_count = conn.execute("SELECT COUNT(*) as c FROM worksheet_final_snapshots").fetchone()["c"]
    
    service.void_snapshot(res.snapshot_id, "Test Reason")
    
    after_row = conn.execute("SELECT * FROM worksheet_final_snapshots WHERE id=?", (res.snapshot_id,)).fetchone()
    after_count = conn.execute("SELECT COUNT(*) as c FROM worksheet_final_snapshots").fetchone()["c"]
    conn.close()
    
    assert before_count == after_count == 1
    assert after_row["status"] == "VOID"
    assert after_row["void_reason"] == "Test Reason"
    assert after_row["voided_at"] is not None
    assert before_row["snapshot_json"] == after_row["snapshot_json"]
    assert before_row["snapshot_hash"] == after_row["snapshot_hash"]
    assert before_row["revision"] == after_row["revision"]

def test_transaction_rollback(temp_db, valid_input):
    service = FinalizationService(db_path=temp_db)
    
    # We patch sqlite3.connect which is called inside get_db_connection
    # to return a connection that fails on commit
    class MockConnection:
        def __init__(self, *args, **kwargs):
            self.conn = sqlite3.connect(temp_db)
            self.conn.row_factory = sqlite3.Row
        
        def execute(self, *args, **kwargs):
            return self.conn.execute(*args, **kwargs)
            
        def commit(self):
            raise sqlite3.DatabaseError("Mock DB Error")
            
        def rollback(self):
            self.conn.rollback()
            
        def close(self):
            self.conn.close()
            
    with patch("core.finalization.get_db_connection", return_value=MockConnection()):
        res = service.finalize(valid_input)
        
    assert res.success is False
    assert "Mock DB Error" in res.message
    
    conn = get_db_connection(temp_db)
    count = conn.execute("SELECT COUNT(*) as c FROM worksheet_final_snapshots").fetchone()["c"]
    conn.close()
    assert count == 0

def _mod_harta(i, **kwargs):
    i.harta_current_rows[0] = replace(i.harta_current_rows[0], **kwargs)

@pytest.mark.parametrize("modify_input_func,expected_error_code", [
    (lambda i: setattr(i, 'npwp', ''), "ID_001"),
    (lambda i: setattr(i, 'nama_wp', ''), "ID_002"),
    (lambda i: setattr(i, 'tahun_pajak', 0), "ID_003"),
    (lambda i: setattr(i, 'harta_current_rows', []), "HRT_001"),
    (lambda i: _mod_harta(i, kode_ct=''), "HRT_002"),
    (lambda i: _mod_harta(i, tahun_perolehan=1800), "HRT_003"),
    (lambda i: _mod_harta(i, nilai_tahun_berjalan='notanumber'), "HRT_004"),
    (lambda i: setattr(i, 'status_ptkp', ''), "PPH_001"),
    (lambda i: setattr(i, 'bupot_rows', [WorksheetBupotRow(jenis="Pekerjaan", npwp_pemberi_kerja="123", no_bupot="123", bruto=-1, pengurang=0)]), "BPT_001"),
    (lambda i: setattr(i, 'is_harta_dirty', True), "DIRTY_001"),
    (lambda i: setattr(i, 'is_pph_dirty', True), "DIRTY_002"),
    (lambda i: setattr(i, 'is_analisis_dirty', True), "DIRTY_003"),
])
def test_blocking_validations(temp_db, valid_input, modify_input_func, expected_error_code):
    modify_input_func(valid_input)
    service = FinalizationService(db_path=temp_db)
    res = service.finalize(valid_input)
    
    assert res.success is False
    assert any(e.code == expected_error_code for e in res.validation_result.errors)

def test_warning_still_can_finalize(temp_db, valid_input):
    valid_input.analisis_result = EvyReconciliationResult(
        total_harta_sebelumnya=10000000.0,
        total_harta_berjalan=15000000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=5000000.0,
        biaya_hidup_setahun=19200000.0,
        pajak_pajak=0.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=24200000.0,
        penghasilan_bruto_umkm=0.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=0.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=30000000.0,
        selisih_pengeluaran_vs_penghasilan=5800000.0,
    )
    
    service = FinalizationService(db_path=temp_db)
    result = service.finalize(valid_input)
    
    assert result.success is True
    assert len(result.validation_result.warnings) > 0
    assert result.validation_result.warnings[0].code == "ANL_001"

def test_snapshot_hash_deterministic(valid_input):
    service = FinalizationService()
    json1, hash1 = service.build_snapshot(valid_input)
    json2, hash2 = service.build_snapshot(valid_input)
    assert hash1 == hash2

def test_changed_payload_changes_hash(valid_input):
    service = FinalizationService()
    _, hash1 = service.build_snapshot(valid_input)
    
    valid_input.bupot_rows[0] = WorksheetBupotRow(
        jenis="Pekerjaan",
        npwp_pemberi_kerja="123456789012345",
        no_bupot="123",
        bruto=200000000.0,
        pengurang=5000000.0,
    )
    _, hash2 = service.build_snapshot(valid_input)
    assert hash1 != hash2
