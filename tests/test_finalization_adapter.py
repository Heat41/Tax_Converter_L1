import unittest
from types import SimpleNamespace

from core.evy_reconciliation import EvyReconciliationResult
from core.finalization_adapter import FinalizationAdapter
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow


def _harta(value, name="Current"):
    return WorksheetHartaRow(
        nomor=1,
        kode_eform="011",
        kode_ct="011",
        nama_harta=name,
        nomor_akun_keterangan="-",
        atas_nama="WP",
        nama_bank="-",
        tahun_perolehan=2020,
        nilai_tahun_sebelumnya=10_000_000.0,
        nilai_tahun_berjalan=float(value),
    )


def _analysis():
    return EvyReconciliationResult(
        total_harta_sebelumnya=10_000_000.0,
        total_harta_berjalan=15_000_000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=5_000_000.0,
        biaya_hidup_setahun=19_200_000.0,
        pajak_pajak=0.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=24_200_000.0,
        penghasilan_bruto_umkm=0.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=0.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=24_200_000.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )


class _FakeWorksheet:
    def __init__(self):
        self.harta_pipeline_result = SimpleNamespace(
            npwp="1234567890123456",
            nama_wp="Budi",
            current_year=2025,
        )
        self.harta_npwp = "1234567890123456"
        self.harta_original_rows = [_harta(10_000_000, "Original")]
        self.harta_saved_rows = [_harta(15_000_000, "Current")]
        self._bupot_saved_rows = [
            WorksheetBupotRow(
                jenis="Pekerjaan",
                npwp_pemberi_kerja="123456789012345",
                no_bupot="BP-1",
                bruto=100_000_000.0,
                pengurang=5_000_000.0,
            )
        ]
        self._pph_saved_components = {"pph_terutang": 1_000_000.0}
        self._saved_status_ptkp = "TK/0"
        self._saved_umkm_bruto = [0.0] * 12
        self._saved_umkm_pph_setor = [0.0] * 12
        self._saved_other_income_state = {"zakat": 5_000_000.0}
        self._saved_final_other_income_rows = []
        self._last_pph_calculation = {"pph_terutang": 1_000_000.0}
        self._last_reconciliation = _analysis()
        self._reconciliation_manual = {"utang_sebelumnya": 0.0}
        self._saved_reconciliation_manual = {"utang_sebelumnya": 0.0}
        self.harta_dirty = False
        self.pph_dirty = False

    def _has_unsaved_harta_changes(self):
        return self.harta_dirty

    def _has_unsaved_bupot_changes(self):
        return self.pph_dirty

    def _has_unsaved_pph_component_changes(self):
        return self.pph_dirty


class TestFinalizationAdapter(unittest.TestCase):
    def test_adapter_uses_saved_current_harta_and_identity(self):
        source = _FakeWorksheet()
        data = FinalizationAdapter.from_worksheet(source)
        self.assertEqual(data.npwp, "1234567890123456")
        self.assertEqual(data.nama_wp, "Budi")
        self.assertEqual(data.tahun_pajak, 2025)
        self.assertEqual(data.harta_current_rows[0].nama_harta, "Current")
        self.assertEqual(data.harta_current_rows[0].nilai_tahun_berjalan, 15_000_000.0)
        self.assertEqual(data.status_ptkp, "TK/0")
        self.assertEqual(data.zakat, 5_000_000.0)

    def test_adapter_forwards_dirty_flags(self):
        source = _FakeWorksheet()
        source.harta_dirty = True
        source.pph_dirty = True
        source._reconciliation_manual = {"utang_sebelumnya": 1.0}
        data = FinalizationAdapter.from_worksheet(source)
        self.assertTrue(data.is_harta_dirty)
        self.assertTrue(data.is_pph_dirty)
        self.assertTrue(data.is_analisis_dirty)


if __name__ == "__main__":
    unittest.main()
