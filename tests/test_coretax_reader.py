import os
import shutil
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from core.coretax_reader import (
    CoretaxReader,
    CoretaxFileInfo,
    CoretaxReadResult,
    CoretaxReaderError,
    UnsupportedFileFormatError,
    EmptyFileError,
    EmptySheetError,
    CorruptedFileError,
)


def create_sample_xls(file_path: str, headers: list, rows: list) -> None:
    """Membuat file biner .xls valid (BIFF2 dengan Windows Latin-1 Codepage) untuk pengujian xlrd."""
    bof = b"\x09\x00\x04\x00\x02\x00\x10\x00"
    codepage = b"\x42\x00\x02\x00\xe4\x04"  # Codepage 1252 (Windows Latin 1)
    nrows = len(rows) + 1
    ncols = len(headers)
    dim = (
        b"\x00\x00\n\x00\x00\x00"
        + nrows.to_bytes(2, "little")
        + b"\x00\x00"
        + ncols.to_bytes(2, "little")
        + b"\x00\x00"
    )

    def make_label(row: int, col: int, text: str) -> bytes:
        tb = str(text).encode("latin1")
        length = 2 + 2 + 3 + 1 + len(tb)
        return (
            b"\x04\x00"
            + length.to_bytes(2, "little")
            + row.to_bytes(2, "little")
            + col.to_bytes(2, "little")
            + b"\x00\x00\x00"
            + len(tb).to_bytes(1, "little")
            + tb
        )

    records = [bof, codepage, dim]
    for c, h in enumerate(headers):
        records.append(make_label(0, c, h))
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            records.append(make_label(r, c, val))
    records.append(b"\x0a\x00\x00\x00")  # EOF record

    with open(file_path, "wb") as f:
        f.write(b"".join(records))


class TestCoretaxReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.reader = CoretaxReader()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_inspect_and_read_xlsx_single_sheet_and_leading_zeros(self):
        """Memastikan pembacaan .xlsx, jumlah baris/kolom, dan preservasi leading zero (NPWP & Kode)."""
        file_path = os.path.join(self.temp_dir, "sample_harta.xlsx")
        df = pd.DataFrame({
            "NPWP": ["001234567890000", "009876543210000"],
            "Kode Harta": ["01001", "02005"],
            "Nama Harta": ["Tabungan BCA", "Mobil Toyota"],
            "Nilai": ["150000000", "300000000"],
            "Keterangan": ["Rekening aktif", "Kondisi baik"],
        })
        df.to_excel(file_path, sheet_name="DataHarta", index=False)

        info = self.reader.inspect_file(file_path)
        self.assertTrue(info.is_excel)
        self.assertFalse(info.is_csv)
        self.assertEqual(info.file_name, "sample_harta.xlsx")
        self.assertEqual(info.sheets, ["DataHarta"])

        result = self.reader.read(file_path)
        self.assertIsInstance(result, CoretaxReadResult)
        self.assertEqual(result.file_name, "sample_harta.xlsx")
        self.assertEqual(result.sheet_name, "DataHarta")
        self.assertEqual(result.headers, ["NPWP", "Kode Harta", "Nama Harta", "Nilai", "Keterangan"])
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.total_columns, 5)

        # Verifikasi eksplisit bahwa leading zero TIDAK hilang
        self.assertEqual(result.rows[0][0], "001234567890000")
        self.assertNotEqual(result.rows[0][0], "1234567890000")
        self.assertEqual(result.rows[0][1], "01001")
        self.assertNotEqual(result.rows[0][1], "1001")

        self.assertEqual(result.rows[1][0], "009876543210000")
        self.assertEqual(result.rows[1][1], "02005")
        self.assertNotEqual(result.rows[1][1], "2005")

    def test_inspect_and_read_xls_format(self):
        """Memastikan file .xls (Excel 97-2003) dapat diinspeksi dan dibaca dengan engine xlrd."""
        file_path = os.path.join(self.temp_dir, "sample_legacy.xls")
        headers = ["NPWP", "Kode Harta", "Nama Harta", "Nilai"]
        rows = [
            ["001234567890000", "01001", "Tabungan Kas", "75000000"],
            ["009876543210000", "02005", "Kendaraan Truk", "350000000"],
        ]
        create_sample_xls(file_path, headers, rows)

        info = self.reader.inspect_file(file_path)
        self.assertTrue(info.is_excel)
        self.assertFalse(info.is_csv)
        self.assertEqual(info.file_name, "sample_legacy.xls")
        self.assertEqual(len(info.sheets), 1)

        result = self.reader.read(file_path)
        self.assertEqual(result.file_name, "sample_legacy.xls")
        self.assertEqual(result.headers, ["NPWP", "Kode Harta", "Nama Harta", "Nilai"])
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.total_columns, 4)

        # Verifikasi data & leading zeroes pada .xls
        self.assertEqual(result.rows[0][0], "001234567890000")
        self.assertEqual(result.rows[0][1], "01001")
        self.assertEqual(result.rows[0][2], "Tabungan Kas")
        self.assertEqual(result.rows[1][0], "009876543210000")
        self.assertEqual(result.rows[1][1], "02005")

    def test_inspect_and_read_xlsx_multi_sheet(self):
        """Memastikan file Excel multi-sheet terdeteksi dan dapat dibaca per sheet."""
        file_path = os.path.join(self.temp_dir, "multi_sheet.xlsx")
        df1 = pd.DataFrame({"Kas": ["1000", "2000"]})
        df2 = pd.DataFrame({"Piutang": ["3000", "4000"], "Debitur": ["PT A", "PT B"]})

        with pd.ExcelWriter(file_path) as writer:
            df1.to_excel(writer, sheet_name="KasBank", index=False)
            df2.to_excel(writer, sheet_name="DaftarPiutang", index=False)

        info = self.reader.inspect_file(file_path)
        self.assertEqual(info.sheets, ["KasBank", "DaftarPiutang"])

        # Read default sheet pertama
        result1 = self.reader.read(file_path)
        self.assertEqual(result1.sheet_name, "KasBank")
        self.assertEqual(result1.headers, ["Kas"])
        self.assertEqual(result1.total_rows, 2)

        # Read specific sheet
        result2 = self.reader.read(file_path, sheet_name="DaftarPiutang")
        self.assertEqual(result2.sheet_name, "DaftarPiutang")
        self.assertEqual(result2.headers, ["Piutang", "Debitur"])
        self.assertEqual(result2.total_rows, 2)
        self.assertEqual(result2.rows[0], ["3000", "PT A"])

    def test_inspect_and_read_csv_leading_zeros(self):
        """Memastikan file .csv terbaca dan leading zeroes NPWP / kode tidak terkonversi ke int."""
        file_path = os.path.join(self.temp_dir, "sample_data.csv")
        csv_content = (
            "NPWP,Kode Harta,Nama WP,Kategori,Nilai\n"
            "001234567890000,01001,PT Maju Jaya,Investasi,500000000\n"
            "008888999900000,02005,CV Makmur,Kendaraan,120000000\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        info = self.reader.inspect_file(file_path)
        self.assertTrue(info.is_csv)
        self.assertFalse(info.is_excel)
        self.assertEqual(info.sheets, [])

        result = self.reader.read(file_path)
        self.assertEqual(result.headers, ["NPWP", "Kode Harta", "Nama WP", "Kategori", "Nilai"])
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.total_columns, 5)

        # Verifikasi leading zeros pada CSV
        self.assertEqual(result.rows[0][0], "001234567890000")
        self.assertNotEqual(result.rows[0][0], "1234567890000")
        self.assertEqual(result.rows[0][1], "01001")

        self.assertEqual(result.rows[1][0], "008888999900000")
        self.assertEqual(result.rows[1][1], "02005")

    def test_file_not_found(self):
        """Memastikan FileNotFoundError dimunculkan jika file tidak ada."""
        non_existent = os.path.join(self.temp_dir, "does_not_exist.xlsx")
        with self.assertRaises(FileNotFoundError):
            self.reader.inspect_file(non_existent)

        with self.assertRaises(FileNotFoundError):
            self.reader.read(non_existent)

    def test_unsupported_file_format(self):
        """Memastikan UnsupportedFileFormatError dimunculkan jika format bukan xlsx/xls/csv."""
        txt_file = os.path.join(self.temp_dir, "sample.txt")
        with open(txt_file, "w") as f:
            f.write("Some text data")

        with self.assertRaises(UnsupportedFileFormatError):
            self.reader.inspect_file(txt_file)

        with self.assertRaises(UnsupportedFileFormatError):
            self.reader.read(txt_file)

    def test_empty_file_zero_bytes(self):
        """Memastikan EmptyFileError dimunculkan pada file 0 bytes."""
        empty_file = os.path.join(self.temp_dir, "empty.xlsx")
        with open(empty_file, "wb") as f:
            pass

        with self.assertRaises(EmptyFileError):
            self.reader.inspect_file(empty_file)

        with self.assertRaises(EmptyFileError):
            self.reader.read(empty_file)

    def test_empty_csv_file(self):
        """Memastikan EmptyFileError dimunculkan pada file CSV kosong."""
        empty_csv = os.path.join(self.temp_dir, "empty.csv")
        with open(empty_csv, "w", encoding="utf-8") as f:
            f.write("")

        with self.assertRaises(EmptyFileError):
            self.reader.inspect_file(empty_csv)

    def test_empty_excel_sheet(self):
        """Memastikan EmptySheetError dimunculkan pada sheet yang tidak memiliki data."""
        file_path = os.path.join(self.temp_dir, "empty_sheet.xlsx")
        df = pd.DataFrame()
        df.to_excel(file_path, sheet_name="Kosong", index=False)

        info = self.reader.inspect_file(file_path)
        self.assertEqual(info.sheets, ["Kosong"])

        with self.assertRaises(EmptySheetError):
            self.reader.read(file_path, sheet_name="Kosong")

    def test_nonexistent_sheet_name(self):
        """Memastikan CoretaxReaderError dimunculkan jika nama sheet tidak ada pada workbook."""
        file_path = os.path.join(self.temp_dir, "single.xlsx")
        df = pd.DataFrame({"A": [1, 2]})
        df.to_excel(file_path, sheet_name="SheetA", index=False)

        with self.assertRaises(CoretaxReaderError):
            self.reader.read(file_path, sheet_name="NonExistentSheet")

    def test_corrupted_excel_file(self):
        """Memastikan CorruptedFileError dimunculkan saat file rusak/bukan format Excel valid."""
        corrupt_file = os.path.join(self.temp_dir, "corrupt.xlsx")
        with open(corrupt_file, "wb") as f:
            f.write(b"NOT_A_VALID_ZIP_OR_EXCEL_STREAM_RANDOM_BYTES")

        with self.assertRaises(CorruptedFileError):
            self.reader.inspect_file(corrupt_file)


if __name__ == "__main__":
    unittest.main()
