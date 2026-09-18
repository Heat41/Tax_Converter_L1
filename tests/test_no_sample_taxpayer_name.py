import unittest
from pathlib import Path


class TestNoSampleTaxpayerName(unittest.TestCase):
    def test_sample_taxpayer_name_is_not_present_in_production_source(self):
        root = Path(__file__).resolve().parents[1]
        forbidden = ("EVY" + " BACHTIAR").casefold()

        offenders = []
        for folder in ("core", "ui"):
            for path in (root / folder).rglob("*.py"):
                text = path.read_text(encoding="utf-8", errors="ignore").casefold()
                if forbidden in text:
                    offenders.append(str(path.relative_to(root)))

        self.assertEqual(
            offenders,
            [],
            f"Nama WP contoh masih ditemukan pada source produksi: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
