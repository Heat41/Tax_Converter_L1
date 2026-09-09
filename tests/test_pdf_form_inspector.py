from __future__ import annotations

import importlib.util
import unittest

from core.legacy_pdf_field_map import expected_acroform_fields
from core.legacy_pdf_template import Legacy1770TemplateManager
from core.pdf_form_inspector import PdfFormInspector


class TestPdfFormInspector(unittest.TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            PdfFormInspector().inspect("__missing_1770_template__.pdf")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf belum terpasang")
    def test_installed_template_contains_stage8c_minimum_fields(self):
        manager = Legacy1770TemplateManager()
        info = manager.inspect()
        if not info.exists:
            self.skipTest("Template 1770 belum dipasang pada resources/templates/1770/1770_blank.pdf")

        fields = PdfFormInspector().inspect(info.path)
        missing = expected_acroform_fields() - set(fields)
        self.assertEqual(missing, set())

        self.assertIn(10, fields["NPWP"].pages)
        self.assertIn(13, fields["IIANPWP1"].pages)
        self.assertIn(15, fields["KodeHarta1"].pages)


if __name__ == "__main__":
    unittest.main()
