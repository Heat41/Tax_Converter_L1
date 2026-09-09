import json

import pytest

from config.database import get_db_connection, init_database
from core.legacy_mapping import CORETAX_TO_EFORM, LegacyFormatMappingService


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "legacy_mapping.db"
    init_database(db_path)
    return db_path


def _insert_final_snapshot(db_path, *, npwp="6101015612710001", year=2025, rows=None):
    payload = {
        "npwp": npwp,
        "nama_wp": "EVY BACHTIAR",
        "tahun_pajak": year,
        "harta_current_rows": rows or [],
    }
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO worksheet_final_snapshots (
                npwp, nama_wp, tahun_pajak, revision, status,
                snapshot_schema_version, snapshot_json, validation_json,
                snapshot_hash
            ) VALUES (?, ?, ?, 1, 'FINAL', 1, ?, '[]', 'hash-test')
            """,
            (npwp, "EVY BACHTIAR", year, json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()


def _row(**overrides):
    data = {
        "nomor": 1,
        "kode_eform": "",
        "kode_ct": "0104",
        "nama_harta": "Deposito",
        "nomor_akun_keterangan": "116801000285407",
        "atas_nama": "DR EVY BACHTIAR SPOG",
        "nama_bank": "BRI",
        "tahun_perolehan": 2022,
        "nilai_tahun_sebelumnya": 3000000000.0,
        "nilai_tahun_berjalan": 3000000000.0,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    ("kode_ct", "kode_eform"),
    [
        ("0101", "011"),
        ("0102", "012"),
        ("0104", "014"),
        ("0201", "021"),
        ("0305", "034"),
        ("0403", "043"),
        ("0501", "061"),
        ("0506", "062"),
        ("0601", "071"),
        ("0701", "051"),
        ("0709", "055"),
        ("0799", "019"),
    ],
)
def test_reference_mapping_codes(kode_ct, kode_eform):
    assert CORETAX_TO_EFORM[kode_ct] == kode_eform


def test_requires_active_final_snapshot(temp_db):
    service = LegacyFormatMappingService(temp_db)
    result = service.map_active_final("6101015612710001", 2025)
    assert result.can_export is False
    assert any(issue.code == "LGC_002" for issue in result.errors)


def test_maps_current_snapshot_to_legacy_model(temp_db):
    _insert_final_snapshot(temp_db, rows=[_row()])
    result = LegacyFormatMappingService(temp_db).map_active_final(
        "6101015612710001", 2025
    )

    assert result.can_export is True
    assert result.revision == 1
    assert result.snapshot_hash == "hash-test"
    assert len(result.rows) == 1
    mapped = result.rows[0]
    assert mapped.kode_eform == "014"
    assert mapped.kode_coretax == "0104"
    assert mapped.kategori == "KAS"
    assert mapped.nilai_tahun_berjalan == 3000000000.0
    assert "116801000285407" in mapped.keterangan
    assert "BRI" in mapped.keterangan


def test_manual_eform_is_preserved_with_mismatch_warning(temp_db):
    _insert_final_snapshot(
        temp_db,
        rows=[_row(kode_eform="012", kode_ct="0104")],
    )
    result = LegacyFormatMappingService(temp_db).map_active_final(
        "6101015612710001", 2025
    )

    assert result.can_export is True
    assert result.rows[0].kode_eform == "012"
    assert any(issue.code == "LGC_102" for issue in result.warnings)


def test_unknown_coretax_code_blocks_mapping(temp_db):
    _insert_final_snapshot(temp_db, rows=[_row(kode_ct="9999")])
    result = LegacyFormatMappingService(temp_db).map_active_final(
        "6101015612710001", 2025
    )

    assert result.can_export is False
    assert any(issue.code == "LGC_103" for issue in result.errors)


def test_invalid_manual_eform_blocks_mapping(temp_db):
    _insert_final_snapshot(
        temp_db,
        rows=[_row(kode_eform="999", kode_ct="0104")],
    )
    result = LegacyFormatMappingService(temp_db).map_active_final(
        "6101015612710001", 2025
    )

    assert result.can_export is False
    assert any(issue.code == "LGC_101" for issue in result.errors)


def test_mapping_uses_only_final_snapshot_rows(temp_db):
    _insert_final_snapshot(
        temp_db,
        rows=[_row(nama_harta="Deposito FINAL", nilai_tahun_berjalan=123456789.0)],
    )
    result = LegacyFormatMappingService(temp_db).map_active_final(
        "6101015612710001", 2025
    )

    assert result.rows[0].nama_harta == "Deposito FINAL"
    assert result.rows[0].nilai_tahun_berjalan == 123456789.0
