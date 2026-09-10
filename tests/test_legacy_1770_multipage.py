from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_multipage import Legacy1770MultipageService
from core.legacy_mapping import LegacyHartaRow


def _bupot(no: int) -> Legacy1770BupotRow:
    return Legacy1770BupotRow(
        nomor=no,
        jenis="BPA1",
        npwp_pemotong=f"{no:016d}",
        no_bupot=f"BP-{no:03d}",
        bruto=1_000_000 + no,
        pengurang=100_000,
        netto=900_000 + no,
        pph_dipotong=10_000 + no,
    )


def _harta(no: int) -> LegacyHartaRow:
    return LegacyHartaRow(
        nomor=no,
        kode_eform="014",
        kode_coretax="0104",
        kategori="KAS",
        nama_harta=f"HARTA {no}",
        nomor_akun_keterangan=f"AKUN-{no}",
        atas_nama="WP TEST",
        nama_bank="BANK TEST",
        tahun_perolehan=2020 + (no % 6),
        nilai_tahun_sebelumnya=1_000_000 * no,
        nilai_tahun_berjalan=1_100_000 * no,
        keterangan=f"AKUN-{no}; WP TEST; BANK TEST",
    )


def _document(*, bupot_count: int, harta_count: int) -> Legacy1770Document:
    rows = [_bupot(i) for i in range(1, bupot_count + 1)]
    return Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP MULTIPAGE",
        tahun_pajak=2025,
        total_netto_bupot=sum(row.netto for row in rows),
        kredit_pajak=sum(row.pph_dipotong for row in rows),
        bupot_rows=rows,
        harta_rows=[_harta(i) for i in range(1, harta_count + 1)],
    )


def test_multipage_plan_for_evy_sized_bupot_set():
    # 24 Bupot: Lampiran I Bagian C = 4 halaman (6 per halaman),
    # Lampiran II = 2 halaman (15 per halaman), Harta 10 = 1 halaman.
    plan = Legacy1770MultipageService().build_plan(
        _document(bupot_count=24, harta_count=10)
    )

    assert plan.employment_rows == 24
    assert plan.lampiran_ii_rows == 24
    assert plan.harta_rows == 10
    assert plan.lampiran_i_c_pages == 4
    assert plan.lampiran_ii_pages == 2
    assert plan.lampiran_iv_pages == 1
    assert plan.extra_pages == 4
    assert plan.output_pages == 10


def test_multipage_plan_scales_for_other_taxpayer_models():
    plan = Legacy1770MultipageService().build_plan(
        _document(bupot_count=31, harta_count=23)
    )

    assert plan.lampiran_i_c_pages == 6
    assert plan.lampiran_ii_pages == 3
    assert plan.lampiran_iv_pages == 3
    assert plan.extra_pages == 9
    assert plan.output_pages == 15


def test_multipage_plan_keeps_single_master_page_when_rows_fit():
    plan = Legacy1770MultipageService().build_plan(
        _document(bupot_count=6, harta_count=10)
    )

    assert plan.lampiran_i_c_pages == 1
    assert plan.lampiran_ii_pages == 1
    assert plan.lampiran_iv_pages == 1
    assert plan.extra_pages == 0
    assert plan.output_pages == 6


def test_multipage_page_calculation_never_returns_zero():
    service = Legacy1770MultipageService()

    assert service._pages_for_rows(0, 6) == 1
    assert service._pages_for_rows(1, 6) == 1
    assert service._pages_for_rows(6, 6) == 1
    assert service._pages_for_rows(7, 6) == 2
    assert service._pages_for_rows(30, 15) == 2
    assert service._pages_for_rows(31, 15) == 3
