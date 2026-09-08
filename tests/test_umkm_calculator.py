import unittest

from core.umkm_calculator import calculate_umkm_monthly


class TestUMKMCalculator(unittest.TestCase):
    def test_all_zero_matches_evy_current_worksheet(self):
        result = calculate_umkm_monthly([0] * 12, [0] * 12)
        self.assertEqual(result.total_bruto, 0)
        self.assertEqual(result.total_pph, 0)
        self.assertEqual(result.total_pph_setor, 0)
        self.assertEqual(result.total_selisih, 0)

    def test_first_500_million_is_not_taxed(self):
        result = calculate_umkm_monthly([400_000_000, 100_000_000])
        self.assertEqual(result.months[0].pph, 0)
        self.assertEqual(result.months[1].pph, 0)
        self.assertEqual(result.total_pph, 0)

    def test_only_excess_above_500_million_is_taxed_at_half_percent(self):
        result = calculate_umkm_monthly([400_000_000, 200_000_000])
        self.assertEqual(result.months[0].pph, 0)
        self.assertEqual(result.months[1].pph, 500_000)
        self.assertEqual(result.total_bruto, 600_000_000)
        self.assertEqual(result.total_pph, 500_000)

    def test_pph_is_incremental_per_month_like_evy_formula(self):
        result = calculate_umkm_monthly([600_000_000, 100_000_000])
        self.assertEqual(result.months[0].pph, 500_000)
        self.assertEqual(result.months[1].pph, 500_000)
        self.assertEqual(result.total_pph, 1_000_000)

    def test_setor_and_selisih_are_calculated(self):
        result = calculate_umkm_monthly(
            [600_000_000],
            [300_000],
        )
        self.assertEqual(result.months[0].pph, 500_000)
        self.assertEqual(result.months[0].pph_setor, 300_000)
        self.assertEqual(result.months[0].selisih, 200_000)
        self.assertEqual(result.total_selisih, 200_000)


if __name__ == "__main__":
    unittest.main()
