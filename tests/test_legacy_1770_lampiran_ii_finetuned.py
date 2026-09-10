from core.legacy_1770 import Legacy1770BupotRow, Legacy1770Document
from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService


def _row(jenis: str):
    return Legacy1770BupotRow(
        nomor=1,
        jenis=jenis,
        npwp_pemotong="0013058839038000",
        no_bupot="2501LZ5NR",
        bruto=1_000_000,
        pengurang=500_000,
        netto=500_000,
    )


def test_lampiran_ii_maps_bpa1_and_bpa2_to_pph_21():
    service = Legacy1770LampiranIIService()

    assert service._jenis_pajak("BPA1") == "PPh Pasal 21"
    assert service._jenis_pajak("BPA2") == "PPh Pasal 21"
    assert service._jenis_pajak("1721-A1") == "PPh Pasal 21"
    assert service._jenis_pajak("1721-A2") == "PPh Pasal 21"


def test_lampiran_ii_finetuned_remains_dynamic_for_snapshot_rows():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="WP MODEL BERBEDA",
        tahun_pajak=2026,
        kredit_pajak=25_000,
        bupot_rows=[_row("BPA2")],
    )

    result = Legacy1770LampiranIIService().map_document(document)

    assert result.can_fill
    assert result.rows[0].jenis_pajak == "PPh Pasal 21"
    assert result.rows[0].npwp_pemotong == "0013058839038000"
    assert result.rows[0].no_bupot == "2501LZ5NR"
    assert result.jumlah_bagian_a == 25_000
