import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from config.database import init_database
from core.evy_reconciliation import EvyReconciliationResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow
from ui.pages.finalization_page import FinalizationPage


app = QApplication.instance() or QApplication(sys.argv)


def _analysis(selisih=0.0):
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
        penghasilan_netto=24_200_000.0 + selisih,
        selisih_pengeluaran_vs_penghasilan=selisih,
    )


class _Worksheet:
    def __init__(self, *, dirty=False, selisih=0.0, source_file=None):
        self.harta_pipeline_result = SimpleNamespace(
            npwp="1234567890123456",
            nama_wp="Budi",
            current_year=2025,
        )
        self.harta_npwp = "1234567890123456"
        row = WorksheetHartaRow(
            nomor=1,
            kode_eform="011",
            kode_ct="011",
            nama_harta="Kas",
            nomor_akun_keterangan="-",
            atas_nama="WP",
            nama_bank="-",
            tahun_perolehan=2020,
            nilai_tahun_sebelumnya=10_000_000.0,
            nilai_tahun_berjalan=15_000_000.0,
            coretax_metadata={
                "source_file": str(source_file) if source_file else "",
            },
        )
        self.harta_original_rows = [row]
        self.harta_saved_rows = [row]
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
        self._saved_other_income_state = {"zakat": 0.0}
        self._saved_final_other_income_rows = []
        self._last_pph_calculation = {"pph_terutang": 1_000_000.0}
        self._last_reconciliation = _analysis(selisih)
        self._reconciliation_manual = {"utang_sebelumnya": 0.0}
        self._saved_reconciliation_manual = {"utang_sebelumnya": 0.0}
        self.dirty = dirty

    def _has_unsaved_harta_changes(self):
        return self.dirty

    def _has_unsaved_bupot_changes(self):
        return False

    def _has_unsaved_pph_component_changes(self):
        return False


class TestFinalizationPage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "finalization.db"
        init_database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _page(self, source):
        page = FinalizationPage(source, db_path=self.db_path)
        self.addCleanup(page.deleteLater)
        return page

    def test_draft_without_errors_enables_finalize(self):
        page = self._page(_Worksheet())
        self.assertEqual(page.identity_labels["status"].text(), "DRAFT")
        self.assertTrue(page.finalize_button.isEnabled())
        self.assertFalse(page.reopen_button.isVisible())
        self.assertFalse(page.export_coretax_button.isEnabled())

    def test_error_disables_finalize(self):
        page = self._page(_Worksheet(dirty=True))
        self.assertFalse(page.finalize_button.isEnabled())
        self.assertGreater(len(page.current_validation.errors), 0)

    def test_warning_does_not_disable_finalize(self):
        page = self._page(_Worksheet(selisih=1000.0))
        self.assertGreater(len(page.current_validation.warnings), 0)
        self.assertTrue(page.finalize_button.isEnabled())

    def test_final_and_void_state_are_rendered(self):
        page = self._page(_Worksheet())
        result = page.service.finalize(page.current_input)
        self.assertTrue(result.success)
        page.refresh_page()
        self.assertEqual(page.identity_labels["status"].text(), "FINAL")
        self.assertIn("Revision 1", page.identity_labels["revision"].text())
        self.assertEqual(page.history_table.rowCount(), 1)
        self.assertTrue(page.export_coretax_button.isEnabled())

        self.assertTrue(page.service.void_snapshot(result.snapshot_id, "test"))
        page.refresh_page()
        self.assertEqual(page.identity_labels["status"].text(), "DRAFT")
        self.assertEqual(page.history_table.item(0, 1).text(), "VOID")
        self.assertFalse(page.export_coretax_button.isEnabled())

    def test_finalization_page_exposes_official_coretax_export_action(self):
        page = self._page(_Worksheet())
        self.assertEqual(page.export_coretax_button.text(), "Export Paket Coretax")
        source = inspect.getsource(FinalizationPage)
        self.assertIn("OfficialCoretaxPackageExporter", source)
        self.assertIn("OfficialCoretaxPackageValidator", source)

    def test_detects_coretax_source_dir_from_row_metadata(self):
        source_dir = Path(self.temp_dir.name) / "source"
        source_dir.mkdir()
        source_file = source_dir / "PIT L1 Harta Kas Setara Kas.xlsx"
        source_file.write_bytes(b"placeholder")

        page = self._page(_Worksheet(source_file=source_file))

        self.assertEqual(
            page._detect_coretax_source_dir(),
            source_dir.resolve(),
        )

    def test_missing_source_file_skips_automatic_reconciliation(self):
        missing = Path(self.temp_dir.name) / "missing" / "source.xlsx"
        page = self._page(_Worksheet(source_file=missing))

        self.assertIsNone(page._detect_coretax_source_dir())

    def test_finalization_page_integrates_physical_reconciliation(self):
        source = inspect.getsource(FinalizationPage)
        self.assertIn("PhysicalSourceExportReconciler", source)
        self.assertIn("Rekonsiliasi sumber", source)
        self.assertIn("_detect_coretax_source_dir", source)

    def test_tables_do_not_use_resize_columns_to_contents(self):
        source = inspect.getsource(FinalizationPage)
        self.assertNotIn("resizeColumnsToContents", source)
        self.assertIn("optimize_table_interaction", source)

    def test_page_uses_global_theme_without_local_stylesheet(self):
        page = self._page(_Worksheet())
        self.assertEqual(page.styleSheet(), "")


if __name__ == "__main__":
    unittest.main()
