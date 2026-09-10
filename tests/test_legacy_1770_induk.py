import pytest

from core.legacy_1770 import Legacy1770Document
from core.legacy_1770_induk import Legacy1770IndukService
from core.legacy_1770_induk_finetuned import Legacy1770IndukService as FineTunedLegacy1770IndukService


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
        status_ptkp="TK/0",
    )


def test_induk_mapping_follows_actual_legacy_field_positions():
    result = Legacy1770IndukService().map_document(_document())

    assert result.can_fill
    assert result.fields["NPWP"] == "6101015612710001"
    assert result.fields["Nama Wajib Pajak"] == "EVY BACHTIAR"
    assert result.fields["Tahun Pajak"] == "2025"

    # Angka 2 = JumlahBagianCinduk; angka 5 = PNInduk.
    assert result.fields["JumlahBagianCinduk"] == "788920417"
    assert result.fields["JumlahBagianD"] == ""
    assert result.fields["PNInduk"] == "788920417"

    assert result.fields["ZakatSumbanganWajib"] == "45000000"
    assert result.fields["PNsetelahZakat"] == "743920417"
    assert result.fields["PNsetelahKompen"] == "743920417"

    # Angka 11 memakai field PhKP pada template, bukan field PKP yang berada
    # di area formula/label sebelah kiri.
    assert result.fields["PTKP"] == "54000000"
    assert result.fields["PhKP"] == "689920000"
    assert result.fields["PPhTerutang"] == "150976000"
    assert result.fields["JumlahPPhTerutang"] == "150976000"
    assert result.fields["IIJBAinduk"] == "105486376"
    assert result.fields["PPhLebihKurang"] == "45489624"
    assert result.fields["PPh25"] == ""
    assert result.fields["JumlahPPh25"] == ""
    assert result.fields["PPhLebihKurangDibayar"] == "45489624"

    # Tidak ada lagi AUTO15 karena nama itu dipakai banyak widget pada template
    # dan sebelumnya menyebabkan angka tercetak di posisi yang salah.
    assert "AUTO15" not in result.fields
    assert "PNUsaha" not in result.fields
    warning_codes = {issue.code for issue in result.issues}
    assert {"INDUK_W01", "INDUK_W02"}.issubset(warning_codes)


def test_induk_mapping_is_data_driven_not_evy_hardcoded():
    document = Legacy1770Document(
        npwp="1111222233334444",
        nama_wp="MODEL UJI BERBEDA",
        tahun_pajak=2024,
        total_netto_bupot=500_000_000,
        penghasilan_neto_lainnya=50_000_000,
        zakat=10_000_000,
        ptkp=67_500_000,
        pkp=472_500_000,
        pph_terutang=60_000_000,
        kredit_pajak=20_000_000,
        pph25=10_000_000,
        kurang_lebih_bayar=30_000_000,
        status_ptkp="K/2",
    )

    result = Legacy1770IndukService().map_document(document)

    assert result.can_fill
    assert result.fields["NPWP"] == "1111222233334444"
    assert result.fields["Nama Wajib Pajak"] == "MODEL UJI BERBEDA"
    assert result.fields["Tahun Pajak"] == "2024"
    assert result.fields["JumlahBagianCinduk"] == "500000000"
    assert result.fields["JumlahBagianD"] == "50000000"
    assert result.fields["PNInduk"] == "550000000"
    assert result.fields["ZakatSumbanganWajib"] == "10000000"
    assert result.fields["PNsetelahZakat"] == "540000000"
    assert result.fields["PNsetelahKompen"] == "540000000"
    assert result.fields["PTKP"] == "67500000"
    assert result.fields["PhKP"] == "472500000"
    assert result.fields["PPhTerutang"] == "60000000"
    assert result.fields["IIJBAinduk"] == "20000000"
    assert result.fields["PPhLebihKurang"] == "40000000"
    assert result.fields["PPh25"] == "10000000"
    assert result.fields["JumlahPPh25"] == "10000000"
    assert result.fields["PPhLebihKurangDibayar"] == "30000000"


class _CanvasProbe:
    def __init__(self):
        self.font = None
        self.draws = []

    def setFont(self, name, size):
        self.font = (name, size)

    def drawCentredString(self, x, y, text):
        self.draws.append((x, y, text))


@pytest.mark.parametrize(
    ("status", "expected_key", "digit"),
    [
        ("TK/0", "TK", "0"),
        ("K/2", "K", "2"),
        ("K/I/1", "KI", "1"),
    ],
)
def test_ptkp_status_renderer_selects_each_model(status, expected_key, digit):
    canvas = _CanvasProbe()
    service = FineTunedLegacy1770IndukService

    service._draw_ptkp_status(canvas, status, service.BASE_WIDTH, service.BASE_HEIGHT)

    assert len(canvas.draws) == 1
    x, _y, rendered_digit = canvas.draws[0]
    expected_x = service.PTKP_DEPENDENT_POINTS[expected_key][0]
    assert x == pytest.approx(expected_x)
    assert rendered_digit == digit


def test_induk_mapping_blocks_missing_identity():
    result = Legacy1770IndukService().map_document(Legacy1770Document())
    assert not result.can_fill
    assert {issue.code for issue in result.errors} == {"INDUK_001", "INDUK_002", "INDUK_003"}
