from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService
from core.legacy_1770_multipage_final import (
    Legacy1770MultipageService,
    MultipagePageSummary,
)
from core.worksheet_pph_state import WorksheetBupotRow
from core.worksheet_workbook_generic import GenericWorksheetWorkbookImporter


def test_worksheet_bupot_row_carries_pph_dipotong():
    row = WorksheetBupotRow(
        jenis="BPA1",
        npwp_pemberi_kerja="0012345678901234",
        no_bupot="BP-001",
        bruto=10_000_000,
        pengurang=500_000,
        pph_dipotong=475_000,
    )

    assert row.netto == 9_500_000
    assert row.pph_dipotong == 475_000


def test_generic_importer_factory_keeps_optional_pph_detail():
    row = GenericWorksheetWorkbookImporter._make_bupot_row(
        "BPA1",
        "0012345678901234",
        "BP-001",
        10_000_000,
        500_000,
        475_000,
    )

    assert row.pph_dipotong == 475_000


def test_lampiran_ii_maps_real_pph_per_bupot_without_allocation():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP TEST",
        tahun_pajak=2025,
        kredit_pajak=750_000,
        bupot_rows=[
            Legacy1770BupotRow(
                nomor=1,
                jenis="BPA1",
                npwp_pemotong="0012345678901234",
                no_bupot="BP-001",
                bruto=10_000_000,
                pengurang=500_000,
                netto=9_500_000,
                pph_dipotong=250_000,
            ),
            Legacy1770BupotRow(
                nomor=2,
                jenis="BPA1",
                npwp_pemotong="0012345678901234",
                no_bupot="BP-002",
                bruto=20_000_000,
                pengurang=1_000_000,
                netto=19_000_000,
                pph_dipotong=500_000,
            ),
        ],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert [row.pph_dipotong for row in result.rows] == [250_000, 500_000]
    assert result.detail_pph_total == 750_000
    assert result.jumlah_bagian_a == 750_000


def test_actual_footer_page_metadata_forces_last_page_to_grand_total():
    original = MultipagePageSummary(
        section="L1",
        page_number=2,
        page_count=4,
        subtotal=57_232_543,
        grand_total=788_920_417,
        subtotal_available=True,
    )

    actual = Legacy1770MultipageService._with_actual_page_metadata(
        original,
        page_number=4,
        page_count=4,
    )

    assert actual.page_number == 4
    assert actual.page_count == 4
    assert Legacy1770MultipageService._display_value_for_summary(actual) == 788_920_417


def test_non_last_page_still_uses_only_its_subtotal():
    summary = MultipagePageSummary(
        section="L4",
        page_number=2,
        page_count=3,
        subtotal=4_051_940_000,
        grand_total=16_268_223_888,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 4_051_940_000
