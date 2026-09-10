from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_multipage_finetuned import Legacy1770MultipageService
from core.legacy_mapping import LegacyHartaRow


def _bupot(no: int, *, pph: float) -> Legacy1770BupotRow:
    return Legacy1770BupotRow(
        nomor=no,
        jenis="BPA1",
        npwp_pemotong=f"{no:016d}",
        no_bupot=f"BP-{no:03d}",
        bruto=1_000_000 + no,
        pengurang=100_000,
        netto=900_000 + no,
        pph_dipotong=pph,
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
        tahun_perolehan=2025,
        nilai_tahun_sebelumnya=0,
        nilai_tahun_berjalan=1_000_000 * no,
        keterangan=f"AKUN-{no}",
    )


def _document(*, bupot_count=24, harta_count=23, detail_pph=True):
    bupot = [
        _bupot(i, pph=(10_000 + i if detail_pph else 0))
        for i in range(1, bupot_count + 1)
    ]
    kredit = sum(row.pph_dipotong for row in bupot) if detail_pph else 105_486_376
    return Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP MULTIPAGE",
        tahun_pajak=2025,
        total_netto_bupot=sum(row.netto for row in bupot),
        kredit_pajak=kredit,
        bupot_rows=bupot,
        harta_rows=[_harta(i) for i in range(1, harta_count + 1)],
    )


def test_page_summaries_split_lampiran_i_and_preserve_grand_total():
    service = Legacy1770MultipageService()
    doc = _document(bupot_count=24, harta_count=10, detail_pph=True)

    summaries = service.build_page_summaries(doc)["L1"]

    assert len(summaries) == 4
    assert all(item.subtotal_available for item in summaries)
    assert [item.page_number for item in summaries] == [1, 2, 3, 4]
    assert sum(item.subtotal or 0 for item in summaries) == doc.total_netto_bupot
    assert all(item.grand_total == doc.total_netto_bupot for item in summaries)


def test_page_summaries_lampiran_ii_use_real_pph_detail_when_reconciled():
    service = Legacy1770MultipageService()
    doc = _document(bupot_count=24, harta_count=10, detail_pph=True)

    summaries = service.build_page_summaries(doc)["L2"]

    assert len(summaries) == 2
    assert all(item.subtotal_available for item in summaries)
    assert summaries[0].subtotal == sum(row.pph_dipotong for row in doc.bupot_rows[:15])
    assert summaries[1].subtotal == sum(row.pph_dipotong for row in doc.bupot_rows[15:])
    assert sum(item.subtotal or 0 for item in summaries) == doc.kredit_pajak
    assert all(item.grand_total == doc.kredit_pajak for item in summaries)


def test_page_summaries_lampiran_ii_do_not_invent_subtotal_without_pph_detail():
    service = Legacy1770MultipageService()
    doc = _document(bupot_count=24, harta_count=10, detail_pph=False)

    summaries = service.build_page_summaries(doc)["L2"]

    assert len(summaries) == 2
    assert all(item.subtotal_available is False for item in summaries)
    assert all(item.subtotal is None for item in summaries)
    assert all(item.grand_total == 105_486_376 for item in summaries)


def test_page_summaries_lampiran_iv_split_harta_and_reconcile_total():
    service = Legacy1770MultipageService()
    doc = _document(bupot_count=1, harta_count=23, detail_pph=True)

    summaries = service.build_page_summaries(doc)["L4"]

    expected_total = sum(row.nilai_tahun_berjalan for row in doc.harta_rows)
    assert len(summaries) == 3
    assert summaries[0].subtotal == sum(
        row.nilai_tahun_berjalan for row in doc.harta_rows[:10]
    )
    assert summaries[1].subtotal == sum(
        row.nilai_tahun_berjalan for row in doc.harta_rows[10:20]
    )
    assert summaries[2].subtotal == sum(
        row.nilai_tahun_berjalan for row in doc.harta_rows[20:]
    )
    assert sum(item.subtotal or 0 for item in summaries) == expected_total
    assert all(item.grand_total == expected_total for item in summaries)


def test_single_page_still_exposes_subtotal_and_total():
    service = Legacy1770MultipageService()
    doc = _document(bupot_count=3, harta_count=3, detail_pph=True)

    summaries = service.build_page_summaries(doc)

    assert len(summaries["L1"]) == 1
    assert len(summaries["L2"]) == 1
    assert len(summaries["L4"]) == 1
    assert summaries["L1"][0].subtotal == summaries["L1"][0].grand_total
    assert summaries["L2"][0].subtotal == summaries["L2"][0].grand_total
    assert summaries["L4"][0].subtotal == summaries["L4"][0].grand_total
