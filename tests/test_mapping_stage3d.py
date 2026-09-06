import unittest

from config.constants import JenisKepemilikan, KategoriL1
from core.mapping.legacy_1770iv import Legacy1770IVMapper
from core.models.asset import HartaL1Item


class TestLegacy1770IVMapperStage3D(unittest.TestCase):
    def setUp(self):
        self.mapper = Legacy1770IVMapper()

    def test_kas_uses_current_value_and_builds_name(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2020,
            nama_bank_institusi="BANK A",
            nomor_akun="001234",
            atas_nama="BUDI",
            lokasi_negara="ID",
            saldo_original=100000000,
            saldo_current=125000000,
            source_file="kas.xlsx",
            source_category="KAS SETARA KAS",
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.kode_harta, "0101")
        self.assertEqual(row.nama_harta, "BANK A - 001234")
        self.assertEqual(row.tahun_perolehan, 2020)
        self.assertEqual(row.harga_perolehan, 125000000.0)
        self.assertIn("Atas nama: BUDI", row.keterangan)
        self.assertIn("Lokasi: ID", row.keterangan)
        self.assertEqual(row.source_file, "kas.xlsx")

    def test_piutang_uses_current_balance(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.PIUTANG,
            kode_harta="0201",
            tahun_perolehan=2021,
            nomor_identitas_pihak_ketiga="327300001",
            nama_pihak_ketiga="PT ALFA",
            nilai_piutang_original=250000000,
            nilai_piutang_current=250000000,
            saldo_piutang_original=200000000,
            saldo_piutang_current=175000000,
            lokasi_negara="ID",
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.nama_harta, "Piutang kepada PT ALFA")
        self.assertEqual(row.harga_perolehan, 175000000.0)
        self.assertIn("Identitas: 327300001", row.keterangan)
        self.assertIn("Nilai piutang: 250000000", row.keterangan)

    def test_investasi_uses_acquisition_cost_not_current_market_value(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.INVESTASI,
            kode_harta="0301",
            tahun_perolehan=2022,
            nama_institusi="BROKER A",
            nomor_akun_bukti="ACC-1",
            biaya_perolehan_original=10000000,
            biaya_perolehan_current=11000000,
            nilai_saat_ini_original=12500000,
            nilai_saat_ini_current=14000000,
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.nama_harta, "BROKER A - ACC-1")
        self.assertEqual(row.harga_perolehan, 11000000.0)
        self.assertIn("Nilai saat ini: 14000000", row.keterangan)

    def test_harta_bergerak_builds_description(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.BERGERAK,
            kode_harta="0401",
            tahun_perolehan=2019,
            merek_model="TOYOTA AVANZA",
            nomor_polisi_registrasi="KB 1234 AA",
            jenis_kepemilikan=JenisKepemilikan.TAXPAYER,
            npwp_pemilik="0123456789012345",
            nama_pemilik="BUDI",
            biaya_perolehan_original=200000000,
            biaya_perolehan_current=190000000,
            nilai_saat_ini_current=150000000,
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.nama_harta, "TOYOTA AVANZA - KB 1234 AA")
        self.assertEqual(row.harga_perolehan, 190000000.0)
        self.assertIn("Pemilik: BUDI", row.keterangan)
        self.assertIn("Kepemilikan: TAXPAYER", row.keterangan)

    def test_harta_tidak_bergerak_builds_property_details(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.HTB,
            kode_harta="0501",
            tahun_perolehan=2018,
            lokasi_alamat="Jl. Merdeka, Pontianak",
            luas_tanah="200",
            luas_bangunan="120",
            sumber_kepemilikan="PEMBELIAN",
            nomor_sertifikat="SHM-1",
            biaya_perolehan_original=800000000,
            biaya_perolehan_current=850000000,
            nilai_saat_ini_current=1000000000,
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.nama_harta, "Jl. Merdeka, Pontianak")
        self.assertEqual(row.harga_perolehan, 850000000.0)
        self.assertIn("Luas tanah: 200", row.keterangan)
        self.assertIn("Luas bangunan: 120", row.keterangan)
        self.assertIn("Sertifikat: SHM-1", row.keterangan)

    def test_lainnya_uses_additional_information(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.LAINNYA,
            kode_harta="0601",
            tahun_perolehan=2023,
            nomor_akun_bukti="DOC-1",
            informasi_tambahan="ASET DIGITAL",
            biaya_perolehan_original=5000000,
            biaya_perolehan_current=5500000,
            nilai_saat_ini_current=6000000,
        )

        row = self.mapper.map_item(item)

        self.assertEqual(row.nama_harta, "ASET DIGITAL")
        self.assertEqual(row.harga_perolehan, 5500000.0)
        self.assertIn("Bukti/Nomor akun: DOC-1", row.keterangan)

    def test_map_items_skips_inactive_by_default(self):
        active = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2020,
            saldo_current=1000,
            is_active=1,
        )
        inactive = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0102",
            tahun_perolehan=2021,
            saldo_current=2000,
            is_active=0,
        )

        rows = self.mapper.map_items([active, inactive])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kode_harta, "0101")

    def test_map_items_can_include_inactive(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2020,
            saldo_current=1000,
            is_active=0,
        )

        rows = self.mapper.map_items([item], include_inactive=True)

        self.assertEqual(len(rows), 1)

    def test_total_acquisition_cost(self):
        first = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2020,
            saldo_current=1000,
        )
        second = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.PIUTANG,
            kode_harta="0201",
            tahun_perolehan=2021,
            saldo_piutang_current=2500,
        )

        rows = self.mapper.map_items([first, second])

        self.assertEqual(self.mapper.total_acquisition_cost(rows), 3500.0)

    def test_as_dict_matches_legacy_columns(self):
        item = HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2020,
            saldo_current=1000,
        )

        output = self.mapper.map_item(item).as_dict()

        self.assertEqual(
            list(output.keys()),
            [
                "Kode Harta",
                "Nama Harta",
                "Tahun Perolehan",
                "Harga Perolehan",
                "Keterangan",
            ],
        )


if __name__ == "__main__":
    unittest.main()
