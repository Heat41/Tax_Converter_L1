import unittest

from core.pph_calculator import (
    PTKP_BY_STATUS,
    calculate_annual_pph,
    progressive_pph,
)


class TestAnnualPPhCalculator(unittest.TestCase):
    def test_ptkp_values_match_production_worksheet_reference(self):
        self.assertEqual(PTKP_BY_STATUS["TK/0"], 54_000_000.0)
        self.assertEqual(PTKP_BY_STATUS["K/0"], 58_500_000.0)
        self.assertEqual(PTKP_BY_STATUS["K/I/3"], 126_000_000.0)

    def test_progressive_layers_match_worksheet_brackets(self):
        self.assertEqual(progressive_pph(60_000_000), 3_000_000.0)
        self.assertEqual(progressive_pph(66_000_000), 3_900_000.0)
        self.assertEqual(progressive_pph(250_000_000), 31_500_000.0)

    def test_lisa_worksheet_golden_case(self):
        result = calculate_annual_pph(
            total_netto_bupot=1_690_375,
            penghasilan_neto_lainnya=54_001_000,
            pengurang_penghasilan_neto=0,
            status_ptkp="TK/0",
            kredit_pajak=84_519,
            pph25=0,
        )

        self.assertEqual(result.penghasilan_neto_sebelum_pengurang, 55_691_000.0)
        self.assertEqual(result.penghasilan_neto_gabungan, 55_691_000.0)
        self.assertEqual(result.ptkp, 54_000_000.0)
        self.assertEqual(result.pkp, 1_691_000.0)
        self.assertEqual(result.pph_terutang, 84_550.0)
        self.assertEqual(result.kurang_lebih_bayar, 31.0)
        self.assertEqual(result.kurang_lebih_bayar_pembulatan, 0.0)


if __name__ == "__main__":
    unittest.main()
