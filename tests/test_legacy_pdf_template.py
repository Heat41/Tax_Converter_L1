from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.legacy_pdf_template import Legacy1770TemplateManager


class _TemplateManager(Legacy1770TemplateManager):
    @staticmethod
    def _page_count(path: Path) -> int:
        return 16


class TestLegacy1770TemplateManager(unittest.TestCase):
    def test_missing_template_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.pdf"
            info = _TemplateManager(path).inspect()
            self.assertFalse(info.exists)
            self.assertFalse(info.is_ready)

    def test_valid_template_can_be_copied_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "1770_blank.pdf"
            source.write_bytes(b"%PDF-FAKE-STAGE8C")
            manager = _TemplateManager(source)

            info = manager.require_ready()
            self.assertTrue(info.exists)
            self.assertEqual(info.page_count, 16)
            self.assertTrue(info.sha256)

            target = Path(tmp) / "work" / "copy.pdf"
            manager.copy_for_export(target)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(source.read_bytes(), b"%PDF-FAKE-STAGE8C")

    def test_indonesian_export_pages_are_locked(self):
        self.assertEqual(
            Legacy1770TemplateManager.INDONESIAN_EXPORT_PAGES,
            (10, 12, 13, 14, 15),
        )


if __name__ == "__main__":
    unittest.main()
