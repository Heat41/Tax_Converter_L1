from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_induk import Legacy1770IndukService


def _document():
    return Legacy1770Document(
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
        total_netto_bupot=788_920_417,
        penghasilan_neto_lainnya=0,
        zakat=45_000_000,
        penghasilan_neto_gabungan=743_920_000,
        ptkp=54_000_000,
        pkp=689_920_000,
        pph_terutang=150_976_000,
        kredit_pajak=105_486_376,
        pph25=0,
        kurang_lebih_bayar=45_489_624,
    )


def test_induk_mapping_follows_legacy_form_calculation_flow():
    result = Legacy1770IndukService().map_document(_document())

    assert result.can_fill
    assert result.fields["NPWP"] == "6101015612710001"
    assert result.fields["Nama Wajib Pajak"] == "EVY BACHTIAR"
    assert result.fields["Tahun Pajak"] == "2025"

    # Angka 2 dan 3.
    assert result.fields["PNInduk"] == "788920417"
    assert result.fields["JumlahBagianD"] == ""

    # Angka 5, 6, 7 dan 9. Angka 7 harus menggunakan nilai aktual 5 - 6,
    # bukan nilai kertas kerja yang sudah dibulatkan ribuan.
    assert result.fields["AUTO15"] == "788920417"
    assert result.fields["ZakatSumbanganWajib"] == "45000000"
    assert result.fields["PNsetelahZakat"] == "743920417"
    assert result.fields["PNsetelahKompen"] == "743920417"

    # Angka 10-16 dan 19.
    assert result.fields["PTKP"] == "54000000"
    assert result.fields["PKP"] == "689920000"
    assert result.fields["PPhTerutang"] == "150976000"
    assert result.fields["JumlahPPhTerutang"] == "150976000"
    assert result.fields["IIJBAinduk"] == "105486376"
    assert result.fields["PPhLebihKurang"] == "45489624"
    assert result.fields["JumlahPPh25"] == ""
    assert result.fields["PPhLebihKurangDibayar"] == "45489624"

    # UMKM final tidak boleh dimasukkan ke angka 1 Induk.
    assert "PNUsaha" not in result.fields
    warning_codes = {issue.code for issue in result.issues}
    assert {"INDUK_W01", "INDUK_W02"}.issubset(warning_codes)


def test_induk_mapping_blocks_missing_identity():
    result = Legacy1770IndukService().map_document(Legacy1770Document())
    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"INDUK_001", "INDUK_002", "INDUK_003"}
