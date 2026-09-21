from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow
from core.worksheet_sorting import sort_bupot_rows, sort_harta_rows


def _harta(no, year, code):
    return WorksheetHartaRow(
        nomor=no,
        kode_eform="019",
        kode_ct=code,
        nama_harta=f"Harta {code}",
        nomor_akun_keterangan="",
        atas_nama="",
        nama_bank="",
        tahun_perolehan=year,
        nilai_tahun_sebelumnya=0,
        nilai_tahun_berjalan=1,
    )


def test_harta_sorted_by_acquisition_year_and_renumbered():
    rows = [
        _harta(1, 2025, "0303"),
        _harta(2, 2021, "0101"),
        _harta(3, 2023, "0201"),
    ]

    ordered = sort_harta_rows(rows)

    assert [row.tahun_perolehan for row in ordered] == [2021, 2023, 2025]
    assert [row.nomor for row in ordered] == [1, 2, 3]


def test_bupot_sorted_by_full_date_year_month_day():
    rows = [
        WorksheetBupotRow(no_bupot="C", tanggal_pemotongan="15/12/2025"),
        WorksheetBupotRow(no_bupot="A", tanggal_pemotongan="4 Juni 2025"),
        WorksheetBupotRow(no_bupot="B", tanggal_pemotongan="20/06/2025"),
    ]

    ordered = sort_bupot_rows(rows)

    assert [row.no_bupot for row in ordered] == ["A", "B", "C"]


def test_bupot_falls_back_to_tahun_and_masa_when_date_missing():
    rows = [
        WorksheetBupotRow(no_bupot="MAR", masa="03", tahun="2025"),
        WorksheetBupotRow(no_bupot="JAN", masa="01", tahun="2025"),
        WorksheetBupotRow(no_bupot="DES-OLD", masa="12", tahun="2024"),
    ]

    ordered = sort_bupot_rows(rows)

    assert [row.no_bupot for row in ordered] == ["DES-OLD", "JAN", "MAR"]


def test_bupot_date_takes_priority_over_fallback_masa():
    rows = [
        WorksheetBupotRow(
            no_bupot="FEB",
            masa="12",
            tahun="2025",
            tanggal_pemotongan="10/02/2025",
        ),
        WorksheetBupotRow(
            no_bupot="NOV",
            masa="01",
            tahun="2025",
            tanggal_pemotongan="10/11/2025",
        ),
    ]

    ordered = sort_bupot_rows(rows)

    assert [row.no_bupot for row in ordered] == ["FEB", "NOV"]
