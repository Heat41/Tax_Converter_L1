import unittest

from core.evy_other_income import FinalOtherIncomeRow, calculate_final_other_income


class TestEvyOtherIncome(unittest.TestCase):
    def test_evy_final_other_income_matches_reference_subtotal(self):
        result = calculate_final_other_income(
            [
                FinalOtherIncomeRow("Deposito BRI", 90_000_000, 0.20),
                FinalOtherIncomeRow("Deposito BSI", 22_500_000, 0.20),
                FinalOtherIncomeRow("Obligasi", 567_000_000, 0.10),
            ]
        )

        self.assertEqual(result.total_dpp, 679_500_000)
        self.assertEqual(result.total_pph, 79_200_000)
        self.assertEqual(result.rows[0].pph, 18_000_000)
        self.assertEqual(result.rows[1].pph, 4_500_000)
        self.assertEqual(result.rows[2].pph, 56_700_000)

    def test_negative_values_are_normalized_to_zero(self):
        result = calculate_final_other_income(
            [FinalOtherIncomeRow("Uji", -100, -0.2)]
        )
        self.assertEqual(result.total_dpp, 0)
        self.assertEqual(result.total_pph, 0)


if __name__ == "__main__":
    unittest.main()
