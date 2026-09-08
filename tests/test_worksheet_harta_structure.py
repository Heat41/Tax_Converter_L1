import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from ui.pages.worksheet_harta_structure import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaStructure(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()
        rows = [
            WorksheetHartaRow(
                nomor=1,
                kode_eform="012",
                kode_ct="0102",
                nama_harta="Tabungan",
                nomor_akun_keterangan="111",
                atas_nama="EVY BACHTIAR",
                nama_bank="BRI",
                tahun_perolehan=2025,
                nilai_tahun_sebelumnya=0,
                nilai_tahun_berjalan=1000000,
            ),
            WorksheetHartaRow(
                nomor=2,
                kode_eform="014",
                kode_ct="0104",
                nama_harta="Deposito",
                nomor_akun_keterangan="222",
                atas_nama="EVY BACHTIAR",
                nama_bank="BRI",
                tahun_perolehan=2022,
                nilai_tahun_sebelumnya=0,
                nilai_tahun_berjalan=2000000,
            ),
        ]
        self.result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=rows,
            current_year=2025,
        )
        self.page.load_harta_preview(self.result)

    def tearDown(self):
        self.page.deleteLater()

    def test_structure_buttons_only_active_in_current_mode(self):
        self.assertFalse(self.page.add_harta_button.isEnabled())
        self.assertFalse(self.page.remove_harta_button.isEnabled())

        self.page._show_harta_mode("current")

        self.assertTrue(self.page.add_harta_button.isEnabled())
        self.assertFalse(self.page.remove_harta_button.isEnabled())

        self.page.harta_table.selectRow(0)
        self.assertTrue(self.page.remove_harta_button.isEnabled())

    def test_add_row_preserves_original_and_marks_structural_change(self):
        self.page._show_harta_mode("current")
        self.page.add_harta_row()

        self.assertEqual(len(self.page.harta_original_rows), 2)
        self.assertEqual(len(self.page.harta_current_rows), 3)
        self.assertEqual(self.page.harta_table.rowCount(), 3)
        self.assertIsNone(self.page.harta_origin_indices[-1])
        self.assertEqual(self.page._count_added_rows(), 1)
        self.assertEqual(self.page._count_deleted_rows(), 0)
        self.assertEqual(self.page.harta_current_rows[-1].tahun_perolehan, 2025)
        self.assertTrue(self.page.save_harta_button.isEnabled())
        self.assertTrue(self.page.reset_harta_button.isEnabled())
        self.assertIn("1 baris ditambah", self.page.harta_status.text())

    def test_delete_original_row_does_not_modify_original_import(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.selectRow(0)

        removed = self.page.remove_selected_harta_rows()

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.page.harta_original_rows), 2)
        self.assertEqual(len(self.page.harta_current_rows), 1)
        self.assertEqual(self.page._count_deleted_rows(), 1)
        self.assertEqual(self.page.harta_current_rows[0].nomor, 1)
        self.assertEqual(self.page.harta_current_rows[0].nama_harta, "Deposito")
        self.assertEqual(self.page.harta_original_rows[0].nama_harta, "Tabungan")
        self.assertIn("1 baris dihapus", self.page.harta_status.text())

    def test_add_then_remove_new_row_returns_to_clean_state(self):
        self.page._show_harta_mode("current")
        self.page.add_harta_row()
        self.assertTrue(self.page._has_unsaved_harta_changes())

        new_index = len(self.page.harta_current_rows) - 1
        self.page.harta_table.selectRow(new_index)
        self.page.remove_selected_harta_rows()

        self.assertEqual(self.page._count_added_rows(), 0)
        self.assertEqual(self.page._count_deleted_rows(), 0)
        self.assertFalse(self.page._has_any_harta_changes())
        self.assertFalse(self.page._has_unsaved_harta_changes())
        self.assertFalse(self.page.save_harta_button.isEnabled())
        self.assertFalse(self.page.reset_harta_button.isEnabled())

    def test_reset_restores_added_and_deleted_rows(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.selectRow(0)
        self.page.remove_selected_harta_rows()
        self.page.add_harta_row()

        self.assertTrue(self.page._has_any_harta_changes())
        self.page.reset_harta_to_import()

        self.assertEqual(self.page.harta_current_rows, self.page.harta_original_rows)
        self.assertEqual(self.page.harta_origin_indices, [0, 1])
        self.assertEqual(self.page.harta_table.rowCount(), 2)
        self.assertEqual(self.page._count_added_rows(), 0)
        self.assertEqual(self.page._count_deleted_rows(), 0)
        self.assertFalse(self.page._has_any_harta_changes())

    def test_save_tracks_structural_changes_without_erasing_diff_to_original(self):
        self.page._show_harta_mode("current")
        self.page.add_harta_row()

        self.assertTrue(self.page._has_unsaved_harta_changes())
        self.page.save_harta_changes()

        self.assertFalse(self.page._has_unsaved_harta_changes())
        self.assertFalse(self.page.save_harta_button.isEnabled())
        self.assertTrue(self.page.reset_harta_button.isEnabled())
        self.assertEqual(self.page._count_added_rows(), 1)
        self.assertIn("tersimpan pada sesi worksheet", self.page.harta_status.text())


if __name__ == "__main__":
    unittest.main()
