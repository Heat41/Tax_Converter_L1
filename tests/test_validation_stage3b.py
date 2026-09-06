import unittest
from pathlib import Path

from core.validation.batch import CoretaxBatchImporter
from core.validation.engine import ValidationEngine


class TestCoretaxValidationStage3B(unittest.TestCase):
    def test_partial_categories_are_allowed(self):
        importer = CoretaxBatchImporter()
        files = [Path("1. PIT L1 Harta Kas Setara Kas 250918.xlsx")]
        result = importer.classify_files(files)

        self.assertEqual(result.found_count, 1)
        self.assertIn("KAS SETARA KAS", result.category_files)
        self.assertFalse(result.errors)
        self.assertEqual(len(result.missing_categories), 5)

    def test_tidak_bergerak_precedes_bergerak(self):
        importer = CoretaxBatchImporter()

        self.assertEqual(
            importer.detect_category(
                Path("PIT L1 Harta Tidak Bergerak 250918.xlsx")
            ),
            "HARTA TIDAK BERGERAK",
        )
        self.assertEqual(
            importer.detect_category(
                Path("PIT L1 Harta Bergerak 250918.xlsx")
            ),
            "HARTA BERGERAK",
        )

    def test_duplicate_category_is_error(self):
        importer = CoretaxBatchImporter()
        files = [
            Path("PIT L1 Harta Piutang 1.xlsx"),
            Path("PIT L1 Harta Piutang 2.xlsx"),
        ]
        result = importer.classify_files(files)

        self.assertIn("PIUTANG", result.duplicate_categories)
        self.assertTrue(
            any(
                issue.code == "DUPLICATE_CATEGORY"
                for issue in result.errors
            )
        )

    def test_invalid_required_npwp_and_positive_number(self):
        engine = ValidationEngine()
        headers = [
            "NPWP*",
            "TAHUN PAJAK*",
            "KODE*",
            "NOMOR AKUN*",
            "ATAS NAMA*",
            "NAMA BANK/ INSTITUSI*",
            "LOKASI HARTA*",
            "TAHUN PEROLEHAN*",
            "SALDO*",
        ]
        rows = [[
            "123",
            "2025",
            "0101",
            "123",
            "DAVID",
            "MANDIRI",
            "Indonesia",
            "2025",
            "-10",
        ]]

        result = engine.validate_rows(
            "KAS SETARA KAS",
            headers,
            rows,
        )
        codes = {issue.code for issue in result.errors}

        self.assertIn("INVALID_NPWP", codes)
        self.assertIn("INVALID_POSITIVE_NUMBER", codes)
        self.assertFalse(result.is_valid)

    def test_empty_reference_set_does_not_reject_code(self):
        engine = ValidationEngine()
        headers = ["NPWP*", "TAHUN PAJAK*", "KODE*"]
        rows = [["1234567890123456", "2025", "9999"]]

        result = engine.validate_rows(
            "KAS SETARA KAS",
            headers,
            rows,
        )

        self.assertFalse(
            any(
                issue.code == "INVALID_REFERENCE"
                for issue in result.errors
            )
        )


if __name__ == "__main__":
    unittest.main()
