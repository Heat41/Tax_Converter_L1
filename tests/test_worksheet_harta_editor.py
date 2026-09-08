import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from ui.pages.worksheet_page import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetHartaEditor(unittest.TestCase):
    def setUp(self):
        self.page = WorksheetPage()
        row = WorksheetHartaRow(
            nomor=1,
            kode_eform="012",
            kode_ct="0102",
            nama_harta="Tabungan (Bank/Lembaga Keuangan)",
            nomor_akun_keterangan="116801005138508",
            atas_nama="EVY BACHTIAR",
            nama_bank="BRI",
            tahun_perolehan=2025,
            nilai_tahun_sebelumnya=0,
            nilai_tahun_berjalan=391742658,
        )
        result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[row],
            current_year=2025,
        )
        self.page.load_harta_preview(result)

    def tearDown(self):
        self.page.deleteLater()

    def test_original_import_is_read_only(self):
        self.assertEqual(self.page.harta_mode, "original")
        for column in range(self.page.harta_table.columnCount()):
            item = self.page.harta_table.item(0, column)
            self.assertFalse(bool(item.flags() & Qt.ItemIsEditable))

    def test_current_mode_is_editable_except_number_column(self):
        self.page._show_harta_mode("current")

        self.assertFalse(
            bool(self.page.harta_table.item(0, 0).flags() & Qt.ItemIsEditable)
        )
        self.assertTrue(
            bool(self.page.harta_table.item(0, 3).flags() & Qt.ItemIsEditable)
        )
        self.assertTrue(
            bool(self.page.harta_table.item(0, 9).flags() & Qt.ItemIsEditable)
        )

    def test_edit_updates_current_and_highlights_changed_cell(self):
        self.page._show_harta_mode("current")
        item = self.page.harta_table.item(0, 9)

        item.setText("400.000.000")

        self.assertEqual(
            self.page.harta_current_rows[0].nilai_tahun_berjalan,
            400000000.0,
        )
        self.assertEqual(
            self.page.harta_original_rows[0].nilai_tahun_berjalan,
            391742658,
        )
        self.assertEqual(item.text(), "400.000.000")
        self.assertEqual(item.background().color(), QColor("#FFF3CD"))
        self.assertTrue(self.page.save_harta_button.isEnabled())
        self.assertTrue(self.page.reset_harta_button.isEnabled())
        self.assertIn("1 sel dikoreksi", self.page.harta_status.text())

    def test_save_keeps_highlight_but_clears_unsaved_state(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.item(0, 5).setText("EVY BACHTIAR, DR")

        self.assertTrue(self.page.save_harta_button.isEnabled())
        self.page.save_harta_changes()

        self.assertFalse(self.page.save_harta_button.isEnabled())
        self.assertTrue(self.page.reset_harta_button.isEnabled())
        self.assertIn("tersimpan pada sesi worksheet", self.page.harta_status.text())
        self.assertEqual(
            self.page.harta_table.item(0, 5).background().color(),
            QColor("#FFF3CD"),
        )

    def test_reset_restores_original_import(self):
        self.page._show_harta_mode("current")
        self.page.harta_table.item(0, 3).setText("Nama Harta Koreksi")
        self.assertEqual(
            self.page.harta_current_rows[0].nama_harta,
            "Nama Harta Koreksi",
        )

        self.page.reset_harta_to_import()

        self.assertEqual(
            self.page.harta_current_rows[0].nama_harta,
            "Tabungan (Bank/Lembaga Keuangan)",
        )
        self.assertEqual(
            self.page.harta_table.item(0, 3).text(),
            "Tabungan (Bank/Lembaga Keuangan)",
        )
        self.assertFalse(self.page.reset_harta_button.isEnabled())

    def test_invalid_year_is_rejected(self):
        self.page._show_harta_mode("current")
        item = self.page.harta_table.item(0, 7)

        item.setText("tahun salah")

        self.assertEqual(self.page.harta_current_rows[0].tahun_perolehan, 2025)
        self.assertEqual(item.text(), "2025")
        self.assertIn("Nilai tidak valid", self.page.harta_status.text())


if __name__ == "__main__":
    unittest.main()
