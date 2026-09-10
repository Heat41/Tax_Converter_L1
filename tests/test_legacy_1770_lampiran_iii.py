from core.legacy_1770 import (
    Legacy1770Document,
    Legacy1770FinalIncomeRow,
)
from core.legacy_1770_lampiran_iii import Legacy1770LampiranIIIService


def _final(keterangan: str, dpp: float, tarif: float):
    return Legacy1770FinalIncomeRow(
        keterangan=keterangan,
        dpp=dpp,
        tarif=tarif,
        pph=round(dpp * tarif),
    )


def test_lampiran_iii_maps_final_income_to_matching_old_form_rows():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP LAMPIRAN TIGA",
        tahun_pajak=2026,
        penghasilan_final_lainnya=[
            _final("Bunga Deposito Bank", 90_000_000, 0.20),
            _final("Bunga Obligasi", 567_000_000, 0.10),
            _final("Dividen", 100_000_000, 0.10),
        ],
    )

    result = Legacy1770LampiranIIIService().map_document(document)
    rows = {row.nomor: row for row in result.final_rows}

    assert result.can_fill
    assert rows[1].dpp == 90_000_000
    assert rows[1].pph == 18_000_000
    assert rows[2].dpp == 567_000_000
    assert rows[2].pph == 56_700_000
    assert rows[14].dpp == 100_000_000
    assert rows[14].pph == 10_000_000
    assert result.jumlah_bagian_a_dpp == 757_000_000
    assert result.jumlah_bagian_a_pph == 84_700_000


def test_lampiran_iii_places_umkm_and_unclassified_final_income_in_row_16():
    document = Legacy1770Document(
        npwp="9999888877776666",
        nama_wp="MODEL WP BERBEDA",
        tahun_pajak=2024,
        umkm_bruto=300_000_000,
        umkm_pph_setor=1_500_000,
        penghasilan_final_lainnya=[
            _final("Penghasilan final kategori khusus internal", 25_000_000, 0.10),
        ],
    )

    result = Legacy1770LampiranIIIService().map_document(document)
    rows = {row.nomor: row for row in result.final_rows}

    assert result.can_fill
    assert rows[16].dpp == 325_000_000
    assert rows[16].pph == 4_000_000
    assert result.jumlah_bagian_a_dpp == 325_000_000
    assert result.jumlah_bagian_a_pph == 4_000_000


def test_lampiran_iii_keeps_aggregate_non_object_income_without_guessing_category():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP BUKAN OBJEK",
        tahun_pajak=2025,
        penghasilan_bukan_objek=50_000_000,
    )

    result = Legacy1770LampiranIIIService().map_document(document)

    assert result.can_fill
    assert result.bukan_objek_rows == {6: 50_000_000}
    assert result.jumlah_bagian_b == 50_000_000
    assert any(issue.code == "L3_W01" for issue in result.warnings)


def test_lampiran_iii_is_not_hardcoded_to_evy_values():
    document = Legacy1770Document(
        npwp="1234567890123456",
        nama_wp="DATA DINAMIS",
        tahun_pajak=2023,
        penghasilan_final_lainnya=[
            _final("Hadiah Undian", 12_345_678, 0.25),
        ],
    )

    result = Legacy1770LampiranIIIService().map_document(document)
    row4 = next(row for row in result.final_rows if row.nomor == 4)

    assert row4.dpp == 12_345_678
    assert row4.pph == round(12_345_678 * 0.25)
    assert result.jumlah_bagian_a_dpp == 12_345_678


def test_lampiran_iii_blocks_missing_identity():
    result = Legacy1770LampiranIIIService().map_document(Legacy1770Document())

    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"L3_001", "L3_002", "L3_003"}
