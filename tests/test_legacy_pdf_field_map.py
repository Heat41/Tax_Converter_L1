from __future__ import annotations

import unittest

from core.legacy_pdf_field_map import (
    INDUK_FIELDS,
    LegacyPdfCompletenessValidator,
    SectionState,
    expected_acroform_fields,
)


class TestLegacyPdfFieldMap(unittest.TestCase):
    def setUp(self):
        self.validator = LegacyPdfCompletenessValidator()

    def test_empty_optional_section_is_allowed(self):
        result = self.validator.validate_record_section("lampiran_ii", [])
        self.assertEqual(result.state, SectionState.EMPTY)
        self.assertTrue(result.can_export)

    def test_complete_bupot_is_available(self):
        result = self.validator.validate_record_section(
            "lampiran_ii",
            [
                {
                    "nama_pemotong": "PT CONTOH",
                    "npwp_pemotong": "001234567890123",
                    "no_bupot": "BP-001",
                    "tanggal_bupot": "31/12/2025",
                    "jenis_pph": "21",
                    "pph_dipotong": 125000.0,
                }
            ],
        )
        self.assertEqual(result.state, SectionState.AVAILABLE)
        self.assertEqual(result.issues, [])

    def test_partial_bupot_is_incomplete_not_empty(self):
        result = self.validator.validate_record_section(
            "lampiran_ii",
            [{"npwp_pemotong": "001234567890123", "no_bupot": "BP-001"}],
        )
        self.assertEqual(result.state, SectionState.INCOMPLETE)
        self.assertTrue(result.can_export)
        self.assertGreater(len(result.issues), 0)

    def test_invalid_flag_blocks_section(self):
        result = self.validator.validate_record_section(
            "lampiran_iv_harta",
            [
                {
                    "kode_harta": "011",
                    "nama_harta": "Kas",
                    "tahun_perolehan": 2025,
                    "harga_perolehan": 1000000.0,
                    "invalid_kode_harta": True,
                }
            ],
        )
        self.assertEqual(result.state, SectionState.INVALID)
        self.assertFalse(result.can_export)

    def test_induk_requires_identity(self):
        result = self.validator.validate_single_section(
            "induk",
            {"npwp": "", "nama_wp": "EVY", "tahun_pajak": 2025},
        )
        self.assertEqual(result.state, SectionState.INCOMPLETE)

    def test_expected_fields_include_real_1770_names(self):
        expected = expected_acroform_fields()
        for field_name in (
            "NPWP",
            "Nama Wajib Pajak",
            "PTKP",
            "PKP",
            "PPhTerutang",
            "IIANPWP1",
            "IIAPPhDipotong1",
            "KodeHarta1",
            "IVHargaPerolehanHarta1",
        ):
            self.assertIn(field_name, expected)

        self.assertEqual(INDUK_FIELDS["pph_terutang"], "PPhTerutang")


if __name__ == "__main__":
    unittest.main()
