from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_lampiran_i import Legacy1770LampiranIService


def _bupot(no: int, npwp: str, bruto: float, pengurang: float, *, nama: str = ""):
    return Legacy1770BupotRow(
        nomor=no,
        jenis="BP21",
        npwp_pemotong=npwp,
        no_bupot=f"BP-{no}",
        bruto=bruto,
        pengurang=pengurang,
        netto=bruto - pengurang,
        nama_pemotong=nama,
    )


def test_lampiran_i_uses_snapshot_bupot_and_domestic_other_values():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="CONTOH WP SATU",
        tahun_pajak=2026,
        total_netto_bupot=225_000,
        penghasilan_neto_lainnya=75_000,
        bupot_rows=[
            _bupot(1, "0001112223334445", 200_000, 50_000, nama="PT SATU"),
            _bupot(2, "0005556667778889", 100_000, 25_000, nama="PT DUA"),
        ],
    )

    result = Legacy1770LampiranIService().map_document(document)

    assert result.can_fill
    assert len(result.employment_rows) == 2
    assert result.employment_rows[0].nama_pemberi_kerja == "PT SATU"
    assert result.employment_rows[0].npwp_pemberi_kerja == "0001112223334445"
    assert result.employment_rows[0].bruto == 200_000
    assert result.employment_rows[0].pengurang == 50_000
    assert result.employment_rows[0].netto == 150_000
    assert result.jumlah_bagian_c == 225_000
    assert result.jumlah_bagian_d == 75_000
    assert not result.errors


def test_lampiran_i_is_not_hardcoded_to_evy_values():
    document = Legacy1770Document(
        npwp="9999888877776666",
        nama_wp="MODEL DATA BERBEDA",
        tahun_pajak=2024,
        total_netto_bupot=8_000_000,
        penghasilan_neto_lainnya=1_250_000,
        bupot_rows=[
            _bupot(1, "1234000099998888", 10_000_000, 2_000_000),
        ],
    )

    result = Legacy1770LampiranIService().map_document(document)

    assert result.can_fill
    assert result.jumlah_bagian_c == 8_000_000
    assert result.jumlah_bagian_d == 1_250_000
    assert result.employment_rows[0].npwp_pemberi_kerja == "1234000099998888"
    assert result.employment_rows[0].netto == 8_000_000
    assert any(issue.code == "L1_W03" for issue in result.warnings)


def test_lampiran_i_warns_when_employment_rows_need_continuation_page():
    rows = [
        _bupot(i, f"{i:016d}", 100_000 * i, 10_000 * i)
        for i in range(1, 9)
    ]
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP DELAPAN BARIS",
        tahun_pajak=2025,
        total_netto_bupot=sum(row.netto for row in rows),
        bupot_rows=rows,
    )

    result = Legacy1770LampiranIService().map_document(document)

    assert result.can_fill
    assert len(result.employment_rows) == 8
    assert result.jumlah_bagian_c == sum(row.netto for row in rows)
    assert any(issue.code == "L1_W02" for issue in result.warnings)


def test_lampiran_i_warns_if_summary_total_differs_from_bupot_rows():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP SELISIH",
        tahun_pajak=2025,
        total_netto_bupot=999_999,
        bupot_rows=[_bupot(1, "0001112223334445", 200_000, 50_000)],
    )

    result = Legacy1770LampiranIService().map_document(document)

    assert result.jumlah_bagian_c == 150_000
    assert any(issue.code == "L1_W01" for issue in result.warnings)


def test_lampiran_i_blocks_missing_identity():
    result = Legacy1770LampiranIService().map_document(Legacy1770Document())

    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"L1_001", "L1_002", "L1_003"}
