import unittest
from pathlib import Path

from config.constants import JenisKepemilikan, KategoriL1
from core.coretax_reader import CoretaxReadResult
from core.mapping.harta_mapper import CoretaxHartaMapper
from core.validation.models import (
    BatchImportResult,
    FileCategoryResult,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TestCoretaxHartaMapperStage3C(unittest.TestCase):
    def setUp(self):
        self.mapper = CoretaxHartaMapper()

    def test_map_kas_preserves_original_and_current(self):
        row = {
            "NPWP*": "0123456789012345",
            "TAHUN PAJAK*": "2025",
            "KODE*": "0101",
            "NOMOR AKUN*": "0012345678",
            "ATAS NAMA*": "BUDI",
            "NAMA BANK/ INSTITUSI*": "BANK A",
            "LOKASI HARTA*": "ID",
            "TAHUN PEROLEHAN*": "2020",
            "SALDO*": "150000000",
            "KETERANGAN": "01",
        }

        item = self.mapper.map_row(
            "KAS SETARA KAS",
            row,
            wp_id=7,
            source_file="kas.xlsx",
            import_batch_id=11,
        )

        self.assertEqual(item.wp_id, 7)
        self.assertEqual(item.kategori_l1, KategoriL1.KAS)
        self.assertEqual(item.kode_harta, "0101")
        self.assertEqual(item.tahun_perolehan, 2020)
        self.assertEqual(item.saldo_original, 150000000.0)
        self.assertEqual(item.saldo_current, 150000000.0)
        self.assertEqual(item.source_category, "KAS SETARA KAS")
        self.assertEqual(item.import_batch_id, 11)

    def test_map_piutang(self):
        row = {
            "Kode Harta *": "0201",
            "Negara Lokasi *": "ID",
            "Nomor Identitas *": "3273",
            "Nama Penerima *": "PT ALFA",
            "Nilai Piutang *": "250000000",
            "Tahun *": "2021",
            "Saldo Piutang *": "175000000",
        }

        item = self.mapper.map_row("PIUTANG", row, wp_id=1)

        self.assertEqual(item.kategori_l1, KategoriL1.PIUTANG)
        self.assertEqual(item.nomor_identitas_pihak_ketiga, "3273")
        self.assertEqual(item.nama_pihak_ketiga, "PT ALFA")
        self.assertEqual(item.nilai_piutang_original, 250000000.0)
        self.assertEqual(item.saldo_piutang_current, 175000000.0)

    def test_map_investasi(self):
        row = {
            "Kode *": "0301",
            "Lokasi Harta *": "ID",
            "Nomor Identitas *": "999",
            "Nama Bank/Institusi/Penerima Investasi *": "BROKER A",
            "Bukti Kepemilikan/Nomor Akun *": "ACC-1",
            "Biaya Perolehan *": "10000000",
            "Tahun Perolehan *": "2022",
            "Nilai Saat Ini *": "12500000",
        }

        item = self.mapper.map_row("INVESTASI", row, wp_id=1)

        self.assertEqual(item.kategori_l1, KategoriL1.INVESTASI)
        self.assertEqual(item.nama_institusi, "BROKER A")
        self.assertEqual(item.nomor_akun_bukti, "ACC-1")
        self.assertEqual(item.biaya_perolehan_original, 10000000.0)
        self.assertEqual(item.nilai_saat_ini_current, 12500000.0)

    def test_map_harta_bergerak(self):
        row = {
            "Kode *": "0401",
            "Merk/Model *": "TOYOTA AVANZA",
            "Nomor Polisi/Registrasi *": "KB 1234 AA",
            "Kepemilikan*": "SENDIRI",
            "NPWP Pemilik*": "0123456789012345",
            "Nama Pemotong Pajak *": "BUDI",
            "Tahun Perolehan *": "2019",
            "Biaya Perolehan *": "200000000",
            "Nilai Saat Ini *": "150000000",
        }

        item = self.mapper.map_row("HARTA BERGERAK", row, wp_id=1)

        self.assertEqual(item.kategori_l1, KategoriL1.BERGERAK)
        self.assertEqual(item.merek_model, "TOYOTA AVANZA")
        self.assertEqual(item.jenis_kepemilikan, JenisKepemilikan.TAXPAYER)
        self.assertEqual(item.biaya_perolehan_current, 200000000.0)

    def test_map_harta_tidak_bergerak(self):
        row = {
            "Kode *": "0501",
            "Lokasi Harta *": "PONTIANAK",
            "Ukuran Properti - Tanah *": "200",
            "Ukuran Properti - Bangunan *": "120",
            "Sumber Kepemilikan *": "PEMBELIAN",
            "Nomor Sertifikat *": "SHM-1",
            "Tahun Perolehan *": "2018",
            "Biaya Perolehan *": "800000000",
            "Nilai Saat Ini *": "1000000000",
        }

        item = self.mapper.map_row("HARTA TIDAK BERGERAK", row, wp_id=1)

        self.assertEqual(item.kategori_l1, KategoriL1.HTB)
        self.assertEqual(item.lokasi_alamat, "PONTIANAK")
        self.assertEqual(item.luas_tanah, "200")
        self.assertEqual(item.nomor_sertifikat, "SHM-1")

    def test_map_lainnya(self):
        row = {
            "Kode *": "0601",
            "Tahun Perolehan *": "2023",
            "Bukti Kepemilikan/Nomor Akun *": "DOC-1",
            "Informasi Tambahan *": "ASET DIGITAL",
            "Biaya Perolehan *": "5000000",
            "Nilai Saat Ini *": "6000000",
        }

        item = self.mapper.map_row("LAINNYA", row, wp_id=1)

        self.assertEqual(item.kategori_l1, KategoriL1.LAINNYA)
        self.assertEqual(item.informasi_tambahan, "ASET DIGITAL")
        self.assertEqual(item.nilai_saat_ini_original, 6000000.0)

    def test_map_batch_skips_only_invalid_rows(self):
        read_result = CoretaxReadResult(
            file_path=Path("kas.xlsx"),
            file_name="kas.xlsx",
            sheet_name="KAS SETARA KAS",
            headers=["KODE*", "TAHUN PEROLEHAN*", "SALDO*"],
            rows=[
                ["0101", "2020", "1000"],
                ["0102", "2021", "2000"],
            ],
            total_rows=2,
            total_columns=3,
        )
        validation = ValidationResult(
            is_valid=False,
            total_rows=2,
            valid_rows=1,
            invalid_rows=1,
            errors=[ValidationIssue(
                3,
                "SALDO*",
                "INVALID_POSITIVE_NUMBER",
                ValidationSeverity.ERROR,
                "invalid",
                "0",
            )],
        )
        category_result = FileCategoryResult(
            category="KAS SETARA KAS",
            file_path=Path("kas.xlsx"),
            status="INVALID",
            read_result=read_result,
            validation=validation,
        )
        batch = BatchImportResult(
            category_results={"KAS SETARA KAS": category_result}
        )

        mapped = self.mapper.map_batch(batch, wp_id=99)

        self.assertEqual(mapped.mapped_rows, 1)
        self.assertEqual(mapped.skipped_rows, 1)
        self.assertEqual(mapped.items[0].kode_harta, "0101")

    def test_rupiah_number_normalization(self):
        self.assertEqual(self.mapper._number("1.250.000,50"), 1250000.50)
        self.assertEqual(self.mapper._number("1,250,000"), 1250000.0)
        self.assertEqual(self.mapper._number("Rp 500000"), 500000.0)


if __name__ == "__main__":
    unittest.main()
