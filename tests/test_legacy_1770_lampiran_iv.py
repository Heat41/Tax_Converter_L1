from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_lampiran_iv import Legacy1770LampiranIVService
from core.legacy_mapping import LegacyHartaRow


def _harta(
    nomor: int,
    *,
    kode: str = "014",
    nama: str = "DEPOSITO",
    tahun: int = 2022,
    nilai: float = 100_000_000,
    keterangan: str = "116801000285407; DR CONTOH; BRI",
) -> LegacyHartaRow:
    return LegacyHartaRow(
        nomor=nomor,
        kode_eform=kode,
        kode_coretax="0104",
        kategori="KAS",
        nama_harta=nama,
        nomor_akun_keterangan="116801000285407",
        atas_nama="DR CONTOH",
        nama_bank="BRI",
        tahun_perolehan=tahun,
        nilai_tahun_sebelumnya=nilai,
        nilai_tahun_berjalan=nilai,
        keterangan=keterangan,
    )


def test_lampiran_iv_maps_harta_and_sums_all_current_values():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP LAMPIRAN EMPAT",
        tahun_pajak=2026,
        harta_rows=[
            _harta(1, nilai=100_000_000),
            _harta(2, kode="031", nama="SAHAM", tahun=2024, nilai=250_000_000),
        ],
    )

    result = Legacy1770LampiranIVService().map_document(document)

    assert result.can_fill
    assert len(result.harta_rows) == 2
    assert result.harta_rows[0].kode_harta == "014"
    assert result.harta_rows[0].harga_perolehan == 100_000_000
    assert result.harta_rows[1].nama_harta == "SAHAM"
    assert result.harta_rows[1].tahun_perolehan == 2024
    assert result.jumlah_bagian_a == 350_000_000
    assert result.utang_rows_count == 0
    assert result.anggota_keluarga_count == 0
    assert any(issue.code == "L4_W03" for issue in result.warnings)


def test_lampiran_iv_is_dynamic_for_other_taxpayer_values():
    document = Legacy1770Document(
        npwp="9999888877776666",
        nama_wp="MODEL WP BERBEDA",
        tahun_pajak=2024,
        harta_rows=[
            _harta(
                1,
                kode="061",
                nama="TANAH DAN BANGUNAN",
                tahun=2018,
                nilai=1_750_000_000,
                keterangan="SERTIFIKAT CONTOH",
            )
        ],
    )

    result = Legacy1770LampiranIVService().map_document(document)

    assert result.can_fill
    assert result.harta_rows[0].kode_harta == "061"
    assert result.harta_rows[0].nama_harta == "TANAH DAN BANGUNAN"
    assert result.harta_rows[0].harga_perolehan == 1_750_000_000
    assert result.jumlah_bagian_a == 1_750_000_000


def test_lampiran_iv_warns_but_totals_all_harta_when_more_than_ten_rows():
    rows = [_harta(i, nilai=i * 1_000_000) for i in range(1, 13)]
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP BANYAK HARTA",
        tahun_pajak=2025,
        harta_rows=rows,
    )

    result = Legacy1770LampiranIVService().map_document(document)

    assert len(result.harta_rows) == 12
    assert result.jumlah_bagian_a == sum(i * 1_000_000 for i in range(1, 13))
    assert any(issue.code == "L4_W02" for issue in result.warnings)


def test_lampiran_iv_allows_empty_harta_without_inventing_rows():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP TANPA HARTA",
        tahun_pajak=2025,
    )

    result = Legacy1770LampiranIVService().map_document(document)

    assert result.can_fill
    assert result.harta_rows == []
    assert result.jumlah_bagian_a == 0
    assert any(issue.code == "L4_W01" for issue in result.warnings)


def test_lampiran_iv_blocks_missing_identity():
    result = Legacy1770LampiranIVService().map_document(Legacy1770Document())

    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"L4_001", "L4_002", "L4_003"}
