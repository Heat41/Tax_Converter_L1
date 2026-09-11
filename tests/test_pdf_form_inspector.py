from __future__ import annotations

import importlib.util
import unittest

from core.legacy_pdf_template import Legacy1770TemplateManager
from core.pdf_form_inspector import PdfFormInspector


class TestPdfFormInspector(unittest.TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            PdfFormInspector().inspect("__missing_1770_template__.pdf")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf belum terpasang")
    def test_installed_production_template_is_static_six_page_master(self):
        manager = Legacy1770TemplateManager()
        info = manager.inspect()
        if not info.exists:
            self.skipTest(
                "Template 1770 belum dipasang pada "
                "resources/templates/1770/1770_master_bersih_6_halaman.pdf"
            )

        self.assertEqual(info.page_count, 6)

        # Stage 8C produksi sekarang memakai master visual statis 6 halaman.
        # Template ini memang tidak memiliki field AcroForm interaktif; exporter
        # mencetak data FINAL ke atas salinan master secara statis.
        fields = PdfFormInspector().inspect(info.path)
        self.assertEqual(fields, {})


if __name__ == "__main__":
    unittest.main()
