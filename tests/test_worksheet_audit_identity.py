import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config.database import init_database
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_state import WorksheetHartaStateStore
from ui.pages.worksheet_audit_identity import WorksheetPage


app = QApplication.instance() or QApplication(sys.argv)


class TestWorksheetAuditIdentity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "audit_identity.db"
        init_database(self.db_path)

        self.page = WorksheetPage()
        self.page.harta_state_store = WorksheetHartaStateStore(self.db_path)

    def tearDown(self):
        self.page.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def _row(atas_nama="EVY BACHTIAR"):
        return WorksheetHartaRow(
            nomor=1,
            kode_eform="012",
            kode_ct="0102",
            nama_harta="Tabungan",
            nomor_akun_keterangan="111",
            atas_nama=atas_nama,
            nama_bank="BRI",
            tahun_perolehan=2025,
            nilai_tahun_sebelumnya=0,
            nilai_tahun_berjalan=1000000,
        )

    def test_audit_identity_uses_pipeline_name_npwp_and_year(self):
        result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[self._row()],
            current_year=2025,
            npwp="1234567890123456",
            nama_wp="EVY BACHTIAR",
        )
        self.page.load_harta_preview(result)

        self.assertEqual(self.page.audit_wp_name_value.text(), "EVY BACHTIAR")
        self.assertEqual(self.page.audit_npwp_value.text(), "1234567890123456")
        self.assertEqual(self.page.audit_year_value.text(), "2025")

    def test_audit_identity_falls_back_to_consistent_owner_name(self):
        result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[self._row("EVY BACHTIAR")],
            current_year=2025,
            npwp="1234567890123456",
        )
        self.page.load_harta_preview(result)

        self.assertEqual(self.page.audit_wp_name_value.text(), "EVY BACHTIAR")

    def test_clear_resets_audit_identity(self):
        result = HartaPipelineResult(
            mapping=HartaMappingResult(),
            worksheet_rows=[self._row()],
            current_year=2025,
            npwp="1234567890123456",
            nama_wp="EVY BACHTIAR",
        )
        self.page.load_harta_preview(result)
        self.page.clear_harta_preview()

        self.assertEqual(self.page.audit_wp_name_value.text(), "-")
        self.assertEqual(self.page.audit_npwp_value.text(), "-")
        self.assertEqual(self.page.audit_year_value.text(), "-")


if __name__ == "__main__":
    unittest.main()
