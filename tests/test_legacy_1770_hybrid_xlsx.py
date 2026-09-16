import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from core.evy_reconciliation import EvyReconciliationResult
from core.finalization import FinalizationInput
from core.legacy_1770_hybrid_xlsx import (
    DATA_BUPOT_SHEET,
    DATA_HARTA_SHEET,
    META_SHEET,
    Legacy1770HybridXlsxService,
)
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow


def _analysis():
    return EvyReconciliationResult(
        total_harta_sebelumnya=10000000.0,
        total_harta_berjalan=15000000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=5000000.0,
        biaya_hidup_setahun=19200000.0,
        pajak_pajak=0.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=24200000.0,
        penghasilan_bruto_umkm=0.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=0.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=24200000.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )


def _input():
    return FinalizationInput(
        npwp="1234567890123456",
        nama_wp="Budi",
        tahun_pajak=2025,
        harta_current_rows=[
            WorksheetHartaRow(
                nomor=1,
                kode_eform="011",
                kode_ct="0101",
                nama_harta="Kas",
                nomor_akun_keterangan="KAS-01",
                atas_nama="BUDI",
                nama_bank="-",
                tahun_perolehan=2020,
                nilai_tahun_sebelumnya=10000000.0,
                nilai_tahun_berjalan=15000000.0,
            )
        ],
        harta_original_hash="original-hash",
        bupot_rows=[
            WorksheetBupotRow(
                jenis="BP21",
                no_bupot="BP-001",
                masa="01",
                tahun="2025",
                sifat="TIDAK FINAL",
                status="NORMAL",
                npwp_penerima="1234567890123456",
                nama_penerima="Budi",
                fasilitas="",
                jenis_pph="Pasal 21",
                kop="21-100-07",
                bruto=500000.0,
                dpp_persen=50.0,
                tarif=5.0,
                pengurang=250000.0,
                pph_dipotong=12500.0,
                bukti="Surat Tagihan",
                no_bukti="DOC-1",
                tanggal_bukti="04/06/2025",
                npwp_pemotong="0072103856707000",
                nama_pemotong="PEMOTONG",
                tanggal_pemotongan="04/06/2025",
                mekanisme_sp2d="",
                no_sp2d="",
                npwp_pemberi_kerja="0072103856707000",
            )
        ],
        pph_components={"pph_terutang": 1000000.0},
        umkm_state={},
        penghasilan_lainnya={},
        zakat=0.0,
        status_ptkp="TK/0",
        pph_calc_result={"pph_terutang": 1000000.0},
        analisis_result=_analysis(),
    )


class TestLegacy1770HybridXlsx(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "hybrid.xlsx"
        self.service = Legacy1770HybridXlsxService()

    def tearDown(self):
        self.temp.cleanup()

    def test_export_builds_hybrid_and_roundtrip_sheets(self):
        result = self.service.export(
            _input(),
            self.path,
            revision=3,
            snapshot_hash="snapshot-abc",
        )
        self.assertTrue(result.ok)

        wb = load_workbook(self.path, data_only=False)
        self.assertEqual(
            wb.sheetnames[:6],
            [
                "01 eForm Induk",
                "02 eForm Lamp I H1",
                "03 Legacy Lamp I H2",
                "04 Legacy Lamp II",
                "05 Legacy Lamp III",
                "06 Legacy Lamp IV",
            ],
        )
        self.assertIn(DATA_HARTA_SHEET, wb.sheetnames)
        self.assertIn(DATA_BUPOT_SHEET, wb.sheetnames)
        self.assertEqual(wb[META_SHEET].sheet_state, "veryHidden")
        self.assertEqual(wb["01 eForm Induk"]["A2"].value, "FORMAT BARU e-FORM")
        self.assertEqual(wb["03 Legacy Lamp I H2"]["A2"].value, "FORMAT LAMA / LEGACY DJP")

    def test_roundtrip_reads_user_edits_and_keeps_provenance(self):
        self.service.export(
            _input(),
            self.path,
            revision=7,
            snapshot_hash="snapshot-final-7",
        )

        wb = load_workbook(self.path)
        harta = wb[DATA_HARTA_SHEET]
        bupot = wb[DATA_BUPOT_SHEET]
        harta["D2"] = "Kas Koreksi"
        harta["J2"] = 17500000
        bupot["M2"] = 600000
        bupot["P2"] = 300000
        bupot["Q2"] = 15000
        wb.save(self.path)

        result = self.service.import_revision(
            self.path,
            expected_npwp="1234567890123456",
            expected_year=2025,
            expected_snapshot_hash="snapshot-final-7",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.base_revision, 7)
        self.assertEqual(result.base_snapshot_hash, "snapshot-final-7")
        self.assertEqual(result.harta_rows[0].nama_harta, "Kas Koreksi")
        self.assertEqual(result.harta_rows[0].nilai_tahun_berjalan, 17500000)
        self.assertEqual(result.bupot_rows[0].bruto, 600000)
        self.assertEqual(result.bupot_rows[0].pengurang, 300000)
        self.assertEqual(result.bupot_rows[0].pph_dipotong, 15000)

    def test_roundtrip_rejects_wrong_wp_or_snapshot(self):
        self.service.export(
            _input(),
            self.path,
            revision=2,
            snapshot_hash="snapshot-2",
        )

        wrong_wp = self.service.import_revision(
            self.path,
            expected_npwp="9999999999999999",
            expected_year=2025,
        )
        self.assertFalse(wrong_wp.ok)
        self.assertTrue(any(i.code == "LX_105" for i in wrong_wp.errors))

        wrong_hash = self.service.import_revision(
            self.path,
            expected_npwp="1234567890123456",
            expected_year=2025,
            expected_snapshot_hash="other-hash",
        )
        self.assertFalse(wrong_hash.ok)
        self.assertTrue(any(i.code == "LX_107" for i in wrong_hash.errors))


if __name__ == "__main__":
    unittest.main()
