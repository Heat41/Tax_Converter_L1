import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.legacy_1770_hybrid_pdf import HybridPdfResult
from core.legacy_1770_static_pdf import Legacy1770StaticPdfService, StaticPdfResult


class TestHybridPdfUiRoute(unittest.TestCase):
    def test_active_final_route_returns_static_compatible_hybrid_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "hybrid.pdf"
            output.write_bytes(b"%PDF-test")
            hybrid_result = HybridPdfResult(
                output_path=output,
                page_count=6,
                size_bytes=9,
                sha256="a" * 64,
            )

            with patch(
                "core.legacy_1770_hybrid_pdf.Legacy1770HybridPdfService.export_active_final",
                return_value=hybrid_result,
            ) as exporter:
                result = Legacy1770StaticPdfService().finalize_active_final(
                    "1234567890123456",
                    2025,
                    output,
                    db_path="dummy.db",
                )

            self.assertIsInstance(result, StaticPdfResult)
            self.assertTrue(result.ok)
            self.assertTrue(result.is_static)
            self.assertEqual(result.page_count, 6)
            self.assertEqual(result.sha256, "a" * 64)
            exporter.assert_called_once_with(
                "1234567890123456",
                2025,
                output,
                template_path=None,
            )


if __name__ == "__main__":
    unittest.main()
