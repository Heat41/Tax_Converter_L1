from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_lampiran_ii import Legacy1770LampiranIIService


def _bupot(
    no: int,
    *,
    jenis: str = "BP21",
    npwp: str = "0013058839038000",
    no_bupot: str = "2501LZ5NR",
    nama: str = "PT CONTOH",
    tanggal: str = "2025-03-31",
    pph: float = 46_519,
):
    return Legacy1770BupotRow(
        nomor=no,
        jenis=jenis,
        npwp_pemotong=npwp,
        no_bupot=no_bupot,
        bruto=1_000_000,
        pengurang=500_000,
        netto=500_000,
        nama_pemotong=nama,
        tanggal_bupot=tanggal,
        pph_dipotong=pph,
    )


def test_lampiran_ii_maps_complete_bupot_and_uses_final_credit_total():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP LAMPIRAN DUA",
        tahun_pajak=2026,
        kredit_pajak=67_869,
        bupot_rows=[
            _bupot(1, pph=46_519),
            _bupot(
                2,
                jenis="PPh 23",
                npwp="0018767327123000",
                no_bupot="2503ADYB7",
                nama="PT DUA",
                tanggal="30/06/2026",
                pph=21_350,
            ),
        ],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert result.can_fill
    assert len(result.rows) == 2
    assert result.rows[0].jenis_pajak == "PPh Pasal 21"
    assert result.rows[0].tanggal_bupot == "31/03/2025"
    assert result.rows[1].jenis_pajak == "PPh Pasal 23"
    assert result.rows[1].npwp_pemotong == "0018767327123000"
    assert result.detail_pph_total == 67_869
    assert result.jumlah_bagian_a == 67_869
    assert not result.warnings


def test_lampiran_ii_is_dynamic_for_other_taxpayer_and_tax_type():
    document = Legacy1770Document(
        npwp="9999888877776666",
        nama_wp="MODEL WP BERBEDA",
        tahun_pajak=2024,
        kredit_pajak=1_250_000,
        bupot_rows=[
            _bupot(
                1,
                jenis="BP26",
                npwp="1234000099998888",
                no_bupot="ABC-2024-001",
                nama="PEMOTONG BERBEDA",
                tanggal="2024/12/31",
                pph=1_250_000,
            )
        ],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert result.can_fill
    assert result.rows[0].jenis_pajak == "PPh Pasal 26"
    assert result.rows[0].tanggal_bupot == "31/12/2024"
    assert result.rows[0].no_bupot == "ABC-2024-001"
    assert result.jumlah_bagian_a == 1_250_000


def test_lampiran_ii_uses_aggregate_credit_when_per_bupot_pph_is_unavailable():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP DATA KERTAS KERJA",
        tahun_pajak=2025,
        kredit_pajak=105_486_376,
        bupot_rows=[
            _bupot(
                1,
                nama="",
                tanggal="",
                pph=0,
                no_bupot="250AK117Z",
            )
        ],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert result.can_fill
    assert result.detail_pph_total == 0
    assert result.jumlah_bagian_a == 105_486_376
    warning_codes = {issue.code for issue in result.warnings}
    assert {"L2_W02", "L2_W03"}.issubset(warning_codes)


def test_lampiran_ii_warns_when_detail_total_differs_from_induk_credit():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP SELISIH",
        tahun_pajak=2025,
        kredit_pajak=100_000,
        bupot_rows=[_bupot(1, pph=75_000)],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert result.detail_pph_total == 75_000
    assert result.jumlah_bagian_a == 100_000
    assert any(issue.code == "L2_W04" for issue in result.warnings)


def test_lampiran_ii_warns_when_more_than_fifteen_rows():
    rows = [
        _bupot(
            i,
            npwp=f"{i:016d}",
            no_bupot=f"BP-{i:02d}",
            pph=1_000 * i,
        )
        for i in range(1, 18)
    ]
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP BANYAK BUPOT",
        tahun_pajak=2025,
        kredit_pajak=sum(row.pph_dipotong for row in rows),
        bupot_rows=rows,
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert len(result.rows) == 17
    assert any(issue.code == "L2_W01" for issue in result.warnings)


def test_lampiran_ii_blocks_missing_identity():
    result = Legacy1770LampiranIIService().map_document(Legacy1770Document())

    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"L2_001", "L2_002", "L2_003"}
