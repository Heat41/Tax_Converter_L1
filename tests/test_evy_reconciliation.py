import unittest

from core.evy_reconciliation import (
    calculate_evy_reconciliation,
    living_cost_for_ptkp,
)


class TestEvyReconciliation(unittest.TestCase):
    def test_living_cost_matches_evy_ptkp_table(self):
        self.assertEqual(living_cost_for_ptkp("TK/0"), 19_200_000)
        self.assertEqual(living_cost_for_ptkp("K/0"), 38_400_000)
        self.assertEqual(living_cost_for_ptkp("K/3"), 96_000_000)
        self.assertEqual(living_cost_for_ptkp("K/I/3"), 76_800_000)

    def test_golden_evy_reconciliation_is_zero(self):
        result = calculate_evy_reconciliation(
            total_harta_sebelumnya=15_009_974_357,
            total_harta_berjalan=16_268_223_888,
            total_utang_sebelumnya=0,
            total_utang_berjalan=0,
            status_ptkp="TK/0",
            pph_umkm_setor=0,
            pph21_terutang=150_976_000,
            sewa_pph=0,
            honor_pph=11_274_124,
            final_other_pph_subtotal=79_200_000,
            final_other_pph_detail=79_200_000,
            pengeluaran_lain_lain=-4_518_411,
            kerugian_keuntungan_penjualan_aset=0,
            utang_baru_atas_kredit=0,
            harta_baru_dari_kredit=0,
            penghasilan_bruto_umkm=0,
            penambahan_penghasilan_bruto_umkm=0,
            margin_usaha=0,
            netto_bupot=788_920_417,
            domestic_other=0,
            pekerjaan_bebas_dpp=0,
            prive_dpp=0,
            hibah_warisan_dpp=50_000_000,
            sewa_dpp=0,
            honor_dpp=75_160_827,
            final_other_dpp=679_500_000,
        )

        self.assertEqual(result.naik_turun_harta_utang, 1_258_249_531)
        self.assertEqual(result.biaya_hidup_setahun, 19_200_000)
        self.assertEqual(result.pajak_pajak, 320_650_124)
        self.assertEqual(result.total_pengeluaran, 1_593_581_244)
        self.assertEqual(result.penghasilan_netto, 1_593_581_244)
        self.assertEqual(result.selisih_pengeluaran_vs_penghasilan, 0)

    def test_harta_credit_is_subtracted_from_total_expense(self):
        result = calculate_evy_reconciliation(
            total_harta_sebelumnya=100,
            total_harta_berjalan=200,
            harta_baru_dari_kredit=25,
        )
        self.assertEqual(result.total_pengeluaran, 100 + 19_200_000 - 25)


if __name__ == "__main__":
    unittest.main()
