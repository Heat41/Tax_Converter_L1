import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.validation.batch import CoretaxBatchImporter


class TestRealCoretaxDataSheet(unittest.TestCase):
    def _write_workbook(self, path: Path, data_rows, specification_name: str):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(data_rows).to_excel(
                writer,
                sheet_name="DATA",
                header=False,
                index=False,
            )
            pd.DataFrame([
                ["Kolom pada excel", "Kolom pada xml", "Petunjuk pengisian", "Contoh Pengisian", "Validasi"],
                ["NPWP*", "TIN", "Petunjuk", "1234567890123456", "16 digit"],
                ["TAHUN PAJAK*", "TaxYear", "Petunjuk", "2025", "4 digit"],
            ]).to_excel(
                writer,
                sheet_name=specification_name,
                header=False,
                index=False,
            )

    def test_kas_prefers_populated_data_sheet_over_specification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "1. PIT L1 Harta Kas Setara Kas 250918.xlsx"
            self._write_workbook(
                path,
                [
                    ["NPWP*", "6101015612710001"],
                    ["TAHUN PAJAK*", "2025"],
                    ["KODE*", "NOMOR AKUN*", "ATAS NAMA*", "NAMA BANK/ INSTITUSI*", "LOKASI HARTA*", "TAHUN PEROLEHAN*", "SALDO*", "KETERANGAN"],
                    ["0102", "116801005138508", "EVY BACHTIAR", "BRI", "Indonesia", "2025", "391742658", ""],
                    ["0104", "116801000285407", "EVY BACHTIAR", "BRI", "Indonesia", "2022", "3000000000", ""],
                ],
                "KAS SETARA KAS",
            )

            result = CoretaxBatchImporter().validate([path])
            item = result.category_results["KAS SETARA KAS"]

            self.assertEqual(item.status, "VALID")
            self.assertFalse(item.is_template)
            self.assertFalse(item.is_nihil)
            self.assertEqual(item.read_result.sheet_name, "DATA")
            self.assertEqual(item.read_result.total_rows, 2)
            self.assertEqual(result.total_rows, 2)

    def test_harta_bergerak_accepts_real_nama_pemilik_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "4. PIT L1 Harta Bergerak 250918.xlsx"
            self._write_workbook(
                path,
                [
                    ["NPWP*", "6101015612710001"],
                    ["TAHUN PAJAK *", "2025"],
                    ["Kode *", "Merk/Model *", "Nomor Polisi/Registrasi *", "Kepemilikan*", "NPWP Pemilik*", "Nama Pemilik *", "Tahun Perolehan *", "Biaya Perolehan *", "Nilai Saat Ini *", "Keterangan"],
                    ["0402", "HONDA BEAT", "KB 2183 T", "TAXPAYER", "6101015612710001", "EVY BACHTIAR", "2009", "11000000", "3000000", ""],
                    ["0403", "MITSUBISHI MIRAGE", "KB 1143 PB", "TAXPAYER", "6101015612710001", "EVY BACHTIAR", "2015", "132000000", "85000000", ""],
                    ["0403", "TOYOTA RAIZE", "KB 1476 PI", "TAXPAYER", "6101015612710001", "EVY BACHTIAR", "2025", "343750000", "325000000", ""],
                ],
                "HARTA BERGERAK",
            )

            result = CoretaxBatchImporter().validate([path])
            item = result.category_results["HARTA BERGERAK"]

            self.assertEqual(item.status, "VALID")
            self.assertEqual(item.read_result.total_rows, 3)
            self.assertEqual(result.total_rows, 3)
            self.assertIn("Nama Pemilik *", item.read_result.headers)


if __name__ == "__main__":
    unittest.main()
