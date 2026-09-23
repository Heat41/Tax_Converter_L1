import tempfile
import unittest
from pathlib import Path

from core.legacy_1770 import Legacy1770Document
from core.legacy_mapping import LegacyMappingIssue
from core.legacy_1770_hybrid_pdf import Legacy1770HybridPdfService


class TestLegacy1770HybridPdf(unittest.TestCase):
    def test_hybrid_pdf_keeps_two_new_pages_then_legacy_pages(self):
        from pypdf import PdfReader
        from reportlab.pdfgen import canvas

        document = Legacy1770Document(
            npwp="1234567890123456",
            nama_wp="Budi",
            tahun_pajak=2025,
            status_ptkp="TK/0",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            new_pdf = root / "new.pdf"
            old_pdf = root / "old.pdf"
            out_pdf = root / "hybrid.pdf"

            Legacy1770HybridPdfService._render_new_pages(document, new_pdf)

            c = canvas.Canvas(str(old_pdf), pagesize=Legacy1770HybridPdfService.LEGAL_SIZE)
            for label in (
                "OLD INDUK",
                "OLD LAMP I H1",
                "OLD LAMP I H2",
                "OLD LAMP II",
                "OLD LAMP III",
                "OLD LAMP IV",
            ):
                c.drawString(72, 860, label)
                c.showPage()
            c.save()

            count = Legacy1770HybridPdfService._merge_hybrid(new_pdf, old_pdf, out_pdf)
            self.assertEqual(count, 6)

            result = Legacy1770HybridPdfService.inspect(out_pdf)
            self.assertTrue(result.ok)

            reader = PdfReader(str(out_pdf))
            self.assertIn("HALAMAN 1", reader.pages[0].extract_text() or "")
            self.assertIn("HALAMAN 2", reader.pages[1].extract_text() or "")
            self.assertIn("OLD LAMP I H2", reader.pages[2].extract_text() or "")
            self.assertIn("OLD LAMP IV", reader.pages[5].extract_text() or "")

            for page in reader.pages:
                self.assertAlmostEqual(float(page.mediabox.width), 612.0, delta=2.0)
                self.assertAlmostEqual(float(page.mediabox.height), 936.0, delta=2.0)


    def test_hybrid_pdf_exposes_mapping_error_instead_of_generic_hpdf004(self):
        document = Legacy1770Document(
            npwp="1234567890123456",
            nama_wp="Budi",
            tahun_pajak=2025,
            issues=[
                LegacyMappingIssue(
                    "LGC_103",
                    "ERROR",
                    "Kode Coretax 9999 belum memiliki mapping ke EFORM.",
                    7,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = Legacy1770HybridPdfService().export_document(
                document,
                Path(temp_dir) / "hybrid.pdf",
            )

        self.assertFalse(result.ok)
        self.assertTrue(any(issue.code == "LGC_103" for issue in result.errors))
        self.assertTrue(
            any("baris Harta 7" in issue.message for issue in result.errors)
        )
        self.assertFalse(any(issue.code == "HPDF_004" for issue in result.errors))


if __name__ == "__main__":
    unittest.main()


def test_hybrid_induk_new_pages_use_10pt_font():
    from core.legacy_1770_hybrid_pdf import Legacy1770HybridPdfService
    assert Legacy1770HybridPdfService.NEW_PAGE_FONT_SIZE == 10.0
