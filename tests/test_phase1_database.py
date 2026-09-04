import unittest
import sqlite3
import os
import json
from pathlib import Path
from config.database import get_db_connection, init_database
from config.constants import KategoriL1, StatusProses, JenisKepemilikan, AuditAction, AuditSource
from core.models.wp import WajibPajak
from core.models.asset import HartaL1Item
from core.models.audit import AuditTrailEntry
from core.models.reference import ReferenceKodeHarta
from core.repository import TaxRepository

class TestPhase1Database(unittest.TestCase):
    """Unit Test Komprehensif Phase 1 - Database & Data Model Layer."""

    def setUp(self):
        # Gunakan database in-memory untuk pengujian independen dan cepat
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        
        # Load schema DDL
        schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema_sqlite.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
            
        # Seed Reference Codes
        from core.seeder import seed_ref_kode_harta
        seed_ref_kode_harta(self.conn)
        
        self.repo = TaxRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    # -------------------------------------------------------------------------
    # TEST 1: Create WP
    # -------------------------------------------------------------------------
    def test_01_create_wp(self):
        wp = WajibPajak(
            npwp="3275017007900006",
            nama_wp="LISA VINATALIA",
            tahun_pajak=2025,
            status_ptkp="TK/0",
            status_proses=StatusProses.BELUM_IMPOR
        )
        wp_id = self.repo.create_wp(wp)
        self.assertIsNotNone(wp_id)
        self.assertGreater(wp_id, 0)

        saved = self.repo.get_wp_by_id(wp_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.nama_wp, "LISA VINATALIA")
        self.assertEqual(saved.npwp, "3275017007900006")
        self.assertEqual(saved.tahun_pajak, 2025)
        self.assertEqual(saved.status_proses, StatusProses.BELUM_IMPOR)

    # -------------------------------------------------------------------------
    # TEST 2: Validate NPWP 16 Digit & Exceptions
    # -------------------------------------------------------------------------
    def test_02_validate_npwp_16_digit(self):
        # Valid 16 digit
        wp_valid = WajibPajak(npwp="1234567890123456", nama_wp="WP Test Valid")
        self.assertEqual(wp_valid.npwp, "1234567890123456")

        # Format dengan titik/strip tetap dinormalisasi jika 16 digit
        wp_formatted = WajibPajak(npwp="12.345.678.9-012.3456", nama_wp="WP Formatted")
        self.assertEqual(wp_formatted.npwp, "1234567890123456")

        # Invalid: kurang dari 16 digit (15 digit format lama)
        with self.assertRaises(ValueError):
            WajibPajak(npwp="012345678901234", nama_wp="NPWP 15 Digit")

        # Invalid: lebih dari 16 digit
        with self.assertRaises(ValueError):
            WajibPajak(npwp="12345678901234567", nama_wp="NPWP 17 Digit")

        # Invalid: nama kosong
        with self.assertRaises(ValueError):
            WajibPajak(npwp="1234567890123456", nama_wp="")

        # Invalid: tahun di luar rentang
        with self.assertRaises(ValueError):
            WajibPajak(npwp="1234567890123456", nama_wp="WP Test", tahun_pajak=1999)

    # -------------------------------------------------------------------------
    # TEST 3: Create Asset KAS
    # -------------------------------------------------------------------------
    def test_03_create_asset_kas(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        kas = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0102",
            tahun_perolehan=2024,
            nomor_akun="0668222229",
            atas_nama="LISA VINATALIA",
            nama_bank_institusi="BCA",
            lokasi_negara="Indonesia",
            saldo_original=1521825000.0,
            saldo_current=1521825000.0,
            keterangan_pps="01"
        )
        asset_id = self.repo.create_asset(kas)
        saved = self.repo.get_asset_by_id(asset_id)
        
        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.KAS)
        self.assertEqual(saved.nomor_akun, "0668222229")
        self.assertEqual(saved.nama_bank_institusi, "BCA")
        self.assertEqual(saved.saldo_original, 1521825000.0)
        self.assertEqual(saved.saldo_current, 1521825000.0)
        self.assertEqual(saved.get_effective_acquisition_cost(), 1521825000.0)

    # -------------------------------------------------------------------------
    # TEST 4: Create Asset PIUTANG
    # -------------------------------------------------------------------------
    def test_04_create_asset_piutang(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        piutang = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.PIUTANG,
            kode_harta="0201",
            tahun_perolehan=2023,
            lokasi_negara="Indonesia",
            nomor_identitas_pihak_ketiga="3275010000000001",
            nama_pihak_ketiga="PT Debitur Sejahtera",
            nilai_piutang_original=500000000.0,
            nilai_piutang_current=500000000.0,
            saldo_piutang_original=250000000.0,
            saldo_piutang_current=250000000.0
        )
        asset_id = self.repo.create_asset(piutang)
        saved = self.repo.get_asset_by_id(asset_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.PIUTANG)
        self.assertEqual(saved.nama_pihak_ketiga, "PT Debitur Sejahtera")
        self.assertEqual(saved.nilai_piutang_original, 500000000.0)
        self.assertEqual(saved.saldo_piutang_current, 250000000.0)
        self.assertEqual(saved.get_effective_acquisition_cost(), 250000000.0)

    # -------------------------------------------------------------------------
    # TEST 5: Create Asset INVESTASI
    # -------------------------------------------------------------------------
    def test_05_create_asset_investasi(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        investasi = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.INVESTASI,
            kode_harta="0302",
            tahun_perolehan=2019,
            lokasi_negara="Indonesia",
            nomor_identitas_pihak_ketiga="0123456789012345",
            nama_institusi="PT. Maximus Graha Sapta",
            nomor_akun_bukti="AKTA - No. 34 / 18 Februari 2019",
            biaya_perolehan_original=500000000.0,
            biaya_perolehan_current=500000000.0,
            nilai_saat_ini_original=650000000.0,
            nilai_saat_ini_current=650000000.0
        )
        asset_id = self.repo.create_asset(investasi)
        saved = self.repo.get_asset_by_id(asset_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.INVESTASI)
        self.assertEqual(saved.nama_institusi, "PT. Maximus Graha Sapta")
        self.assertEqual(saved.biaya_perolehan_current, 500000000.0)
        self.assertEqual(saved.nilai_saat_ini_current, 650000000.0)

    # -------------------------------------------------------------------------
    # TEST 6: Create Asset BERGERAK
    # -------------------------------------------------------------------------
    def test_06_create_asset_bergerak(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        mobil = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.BERGERAK,
            kode_harta="0403",
            tahun_perolehan=2022,
            merek_model="HONDA CR-V 1.5 TURBO",
            nomor_polisi_registrasi="B 1234 XYZ",
            jenis_kepemilikan=JenisKepemilikan.TAXPAYER,
            npwp_pemilik="3275017007900006",
            nama_pemilik="LISA VINATALIA",
            biaya_perolehan_original=550000000.0,
            biaya_perolehan_current=550000000.0,
            nilai_saat_ini_original=420000000.0,
            nilai_saat_ini_current=420000000.0
        )
        asset_id = self.repo.create_asset(mobil)
        saved = self.repo.get_asset_by_id(asset_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.BERGERAK)
        self.assertEqual(saved.merek_model, "HONDA CR-V 1.5 TURBO")
        self.assertEqual(saved.nomor_polisi_registrasi, "B 1234 XYZ")
        self.assertEqual(saved.jenis_kepemilikan, JenisKepemilikan.TAXPAYER)

    # -------------------------------------------------------------------------
    # TEST 7: Create Asset HTB (Harta Tidak Bergerak)
    # -------------------------------------------------------------------------
    def test_07_create_asset_htb(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        rumah = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.HTB,
            kode_harta="0502",
            tahun_perolehan=2018,
            lokasi_alamat="Jl. Boulevard Raya Blok A1 No. 5 Jakarta Utara",
            luas_tanah="200 m2",
            luas_bangunan="250 m2",
            sumber_kepemilikan="Own Income",
            nomor_sertifikat="SHM No. 12345/Kelapa Gading",
            biaya_perolehan_original=2500000000.0,
            biaya_perolehan_current=2500000000.0,
            nilai_saat_ini_original=3500000000.0,
            nilai_saat_ini_current=3500000000.0
        )
        asset_id = self.repo.create_asset(rumah)
        saved = self.repo.get_asset_by_id(asset_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.HTB)
        self.assertEqual(saved.luas_tanah, "200 m2")
        self.assertEqual(saved.nomor_sertifikat, "SHM No. 12345/Kelapa Gading")

    # -------------------------------------------------------------------------
    # TEST 8: Create Asset LAINNYA
    # -------------------------------------------------------------------------
    def test_08_create_asset_lainnya(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        emas = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.LAINNYA,
            kode_harta="0701",
            tahun_perolehan=2010,
            informasi_tambahan="Logam Mulia Antam 100 Gram",
            biaya_perolehan_original=50000000.0,
            biaya_perolehan_current=50000000.0,
            nilai_saat_ini_original=140000000.0,
            nilai_saat_ini_current=140000000.0
        )
        asset_id = self.repo.create_asset(emas)
        saved = self.repo.get_asset_by_id(asset_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved.kategori_l1, KategoriL1.LAINNYA)
        self.assertEqual(saved.informasi_tambahan, "Logam Mulia Antam 100 Gram")

    # -------------------------------------------------------------------------
    # TEST 9: Original Value Tidak Berubah Saat Current Value Dikoreksi
    # -------------------------------------------------------------------------
    def test_09_original_value_immutable_on_edit(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        item = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2024,
            saldo_original=1160000000.0,
            saldo_current=1160000000.0
        )
        asset_id = self.repo.create_asset(item)

        # Lakukan koreksi nilai current
        self.repo.update_asset_field_with_audit(asset_id, "saldo_current", 200000000.0, "Koreksi kas fisik akhir tahun")

        updated = self.repo.get_asset_by_id(asset_id)
        # 1. Nilai Current BERUBAH
        self.assertEqual(updated.saldo_current, 200000000.0)
        # 2. Nilai Original TETAP TIDAK BERUBAH (IMMUTABLE)
        self.assertEqual(updated.saldo_original, 1160000000.0)
        # 3. Flag is_edited aktif
        self.assertEqual(updated.is_edited, 1)

        # 4. Percobaan mengubah field original secara langsung harus ditolak
        with self.assertRaises(ValueError):
            self.repo.update_asset_field_with_audit(asset_id, "saldo_original", 500.0)

    # -------------------------------------------------------------------------
    # TEST 10: Audit Trail Tercatat
    # -------------------------------------------------------------------------
    def test_10_audit_trail_recorded(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        item = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.INVESTASI,
            kode_harta="0302",
            tahun_perolehan=2019,
            biaya_perolehan_original=500000000.0,
            biaya_perolehan_current=500000000.0
        )
        asset_id = self.repo.create_asset(item)

        # Update 1
        self.repo.update_asset_field_with_audit(asset_id, "biaya_perolehan_current", 550000000.0, "Penambahan modal")
        # Update 2
        self.repo.update_asset_field_with_audit(asset_id, "nomor_akun_bukti", "Akta No. 99/2025", "Perubahan no akta")

        logs = self.repo.get_audit_trail_by_wp(wp_id)
        self.assertEqual(len(logs), 2)
        
        self.assertEqual(logs[0].nama_kolom, "biaya_perolehan_current")
        self.assertEqual(float(logs[0].nilai_lama), 500000000.0)
        self.assertEqual(float(logs[0].nilai_baru), 550000000.0)
        self.assertEqual(logs[0].action, AuditAction.UPDATE)
        self.assertEqual(logs[0].source, AuditSource.USER_EDIT)
        self.assertEqual(logs[0].keterangan, "Penambahan modal")

        self.assertEqual(logs[1].nama_kolom, "nomor_akun_bukti")
        self.assertEqual(logs[1].nilai_baru, "Akta No. 99/2025")

    # -------------------------------------------------------------------------
    # TEST 11: 35 Reference Mapping Codes Tersedia
    # -------------------------------------------------------------------------
    def test_11_all_35_ref_codes_available(self):
        codes = self.repo.get_all_ref_codes()
        # Jumlah baris master mapping (termasuk sub-mapping 1:N)
        self.assertGreaterEqual(len(codes), 35)

        # Cek beberapa kode kunci
        eform_011 = self.repo.get_eform_code_for_coretax("0101")
        self.assertIsNotNone(eform_011)
        self.assertEqual(eform_011.kode_eform, "011")

        eform_043 = self.repo.get_eform_code_for_coretax("0403")
        self.assertIsNotNone(eform_043)
        self.assertEqual(eform_043.kode_eform, "043")

    # -------------------------------------------------------------------------
    # TEST 12: Mapping 1:N Dapat Direpresentasikan
    # -------------------------------------------------------------------------
    def test_12_mapping_1_to_n(self):
        # E-Form 051 (Logam Mulia) -> Coretax 0701 (Emas Batangan) & 0702 (Emas Perhiasan)
        mappings_051 = self.repo.get_coretax_codes_for_eform("051")
        self.assertEqual(len(mappings_051), 2)
        ct_codes = [m.kode_coretax for m in mappings_051]
        self.assertIn("0701", ct_codes)
        self.assertIn("0702", ct_codes)

        # E-Form 061 (Tempat Tinggal) -> Coretax 0501 (Tanah Kosong) & 0502 (Rumah Tinggal)
        mappings_061 = self.repo.get_coretax_codes_for_eform("061")
        self.assertEqual(len(mappings_061), 2)
        ct_codes_061 = [m.kode_coretax for m in mappings_061]
        self.assertIn("0501", ct_codes_061)
        self.assertIn("0502", ct_codes_061)

    # -------------------------------------------------------------------------
    # TEST 13: Foreign Key WP -> Asset Bekerja & Safety Protection
    # -------------------------------------------------------------------------
    def test_13_foreign_key_protection(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        self.repo.create_asset(HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0101",
            tahun_perolehan=2024,
            saldo_original=1000000.0,
            saldo_current=1000000.0
        ))

        # Mencoba delete WP tanpa force saat masih memiliki aset harus gagal
        with self.assertRaises(ValueError):
            self.repo.delete_wp(wp_id, force=False)

        # Hapus dengan force=True berhasil
        self.repo.delete_wp(wp_id, force=True)
        self.assertIsNone(self.repo.get_wp_by_id(wp_id))
        self.assertEqual(len(self.repo.get_assets_by_wp(wp_id)), 0)

    # -------------------------------------------------------------------------
    # TEST 14: Re-import Tidak Menghapus Audit History & Mendukung Preserve
    # -------------------------------------------------------------------------
    def test_14_reimport_preserves_audit_and_corrections(self):
        wp_id = self.repo.create_wp(WajibPajak(npwp="3275017007900006", nama_wp="LISA"))
        
        # 1. Impor Pertama
        initial_asset = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0102",
            tahun_perolehan=2024,
            nomor_akun="0668222229",
            saldo_original=1521825000.0,
            saldo_current=1521825000.0
        )
        asset_id = self.repo.create_asset(initial_asset)

        # 2. User melakukan koreksi
        self.repo.update_asset_field_with_audit(asset_id, "saldo_current", 1800000000.0, "Koreksi rek koran")
        
        logs_before = self.repo.get_audit_trail_by_wp(wp_id)
        self.assertEqual(len(logs_before), 1)

        # 3. User melakukan Re-import file baru Coretax (dengan nilai Coretax terupdate 1600000000.0)
        reimport_asset = HartaL1Item(
            wp_id=wp_id,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0102",
            tahun_perolehan=2024,
            nomor_akun="0668222229",
            saldo_original=1600000000.0,
            saldo_current=1600000000.0
        )

        res = self.repo.reimport_assets(wp_id, [reimport_asset], strategy="PRESERVE_CORRECTIONS")
        self.assertEqual(res["status"], "SUCCESS")

        # 4. Verifikasi hasil re-import:
        # Aset aktif sekarang memiliki nilai original baru (1600000000.0)
        # tetapi koreksi user sebelumnya (1800000000.0) tetap dipreservasi!
        active_assets = self.repo.get_assets_by_wp(wp_id, only_active=True)
        self.assertEqual(len(active_assets), 1)
        current_active = active_assets[0]
        self.assertEqual(current_active.saldo_original, 1600000000.0)
        self.assertEqual(current_active.saldo_current, 1800000000.0)
        self.assertEqual(current_active.is_edited, 1)

        # 5. Audit trail lama TIDAK HILANG
        logs_after = self.repo.get_audit_trail_by_wp(wp_id)
        self.assertGreater(len(logs_after), len(logs_before))

if __name__ == '__main__':
    unittest.main()
