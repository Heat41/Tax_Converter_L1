import unittest
from types import SimpleNamespace

from core.finalization_adapter import FinalizationAdapter


class _WorksheetStub:
    harta_pipeline_result = None
    _last_reconciliation = object()


class TestFinalizationAdapterStaleState(unittest.TestCase):
    def test_without_active_pipeline_does_not_reuse_previous_analysis(self):
        data = FinalizationAdapter.from_worksheet(_WorksheetStub())
        self.assertIsNone(data.analisis_result)
        self.assertEqual(data.status_ptkp, "")

    def test_missing_ptkp_does_not_expose_default_or_stale_analysis(self):
        worksheet = _WorksheetStub()
        worksheet.harta_pipeline_result = SimpleNamespace(
            npwp="6101015612710001",
            nama_wp="WP UJI",
            current_year=2025,
        )
        worksheet.harta_npwp = "6101015612710001"
        worksheet.harta_original_rows = []
        worksheet.harta_saved_rows = []
        worksheet.harta_current_rows = []
        worksheet._bupot_saved_rows = []
        worksheet._pph_saved_components = {}
        worksheet._saved_status_ptkp = ""
        worksheet._status_ptkp = ""
        worksheet._saved_umkm_bruto = []
        worksheet._saved_umkm_pph_setor = []
        worksheet._saved_other_income_state = {}
        worksheet._saved_final_other_income_rows = []
        worksheet._last_pph_calculation = None
        worksheet._reconciliation_manual = {}
        worksheet._saved_reconciliation_manual = {}
        worksheet._has_unsaved_harta_changes = lambda: False
        worksheet._has_unsaved_bupot_changes = lambda: False
        worksheet._has_unsaved_pph_component_changes = lambda: False

        data = FinalizationAdapter.from_worksheet(worksheet)

        self.assertIsNone(data.analisis_result)
        self.assertEqual(data.status_ptkp, "")
        self.assertEqual(data.harta_current_rows, [])
        self.assertEqual(data.bupot_rows, [])


if __name__ == "__main__":
    unittest.main()
