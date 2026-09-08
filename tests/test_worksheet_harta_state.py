import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from config.database import init_database
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_state import WorksheetHartaStateStore


class TestWorksheetHartaStateStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "worksheet_state.db"
        init_database(self.db_path)
        self.store = WorksheetHartaStateStore(self.db_path)
        self.original = [
            WorksheetHartaRow(
                nomor=1,
                kode_eform="012",
                kode_ct="0102",
                nama_harta="Tabungan",
                nomor_akun_keterangan="111",
                atas_nama="WP",
                nama_bank="BRI",
                tahun_perolehan=2025,
                nilai_tahun_sebelumnya=0,
                nilai_tahun_berjalan=1000000,
            ),
            WorksheetHartaRow(
                nomor=2,
                kode_eform="034",
                kode_ct="0305",
                nama_harta="Obligasi",
                nomor_akun_keterangan="BOND-1",
                atas_nama="WP",
                nama_bank="-",
                tahun_perolehan=2024,
                nilai_tahun_sebelumnya=0,
                nilai_tahun_berjalan=2000000,
            ),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _manual_row(self, name="Harta Manual"):
        return WorksheetHartaRow(
            nomor=2,
            kode_eform="099",
            kode_ct="0999",
            nama_harta=name,
            nomor_akun_keterangan="MANUAL-1",
            atas_nama="WP",
            nama_bank="-",
            tahun_perolehan=2025,
            nilai_tahun_sebelumnya=0,
            nilai_tahun_berjalan=500000,
        )

    def test_save_load_and_audit_add_edit_delete(self):
        current = [
            replace(self.original[0], atas_nama="WP EDITED"),
            self._manual_row(),
        ]
        result = self.store.save_state(
            npwp="1234567890123456",
            tahun_pajak=2025,
            original_rows=self.original,
            current_rows=current,
            origin_indices=[0, None],
        )

        self.assertEqual(result.add_count, 1)
        self.assertEqual(result.edit_count, 1)
        self.assertEqual(result.delete_count, 1)
        self.assertEqual(result.audit_count, 3)

        restored = self.store.load_matching(
            "1234567890123456",
            2025,
            self.original,
        )
        self.assertIsNotNone(restored)
        self.assertEqual(restored.current_rows, current)
        self.assertEqual(restored.origin_indices, [0, None])

        actions = sorted(
            row["action"] for row in self.store.get_audit_rows(result.state_id)
        )
        self.assertEqual(actions, ["ADD", "DELETE", "EDIT"])

    def test_resave_and_fingerprint_isolation(self):
        current = [replace(self.original[0], atas_nama="EDIT"), self.original[1]]
        first = self.store.save_state(
            npwp="1234567890123456",
            tahun_pajak=2025,
            original_rows=self.original,
            current_rows=current,
            origin_indices=[0, 1],
        )
        second = self.store.save_state(
            npwp="1234567890123456",
            tahun_pajak=2025,
            original_rows=self.original,
            current_rows=current,
            origin_indices=[0, 1],
        )
        self.assertEqual(first.audit_count, 1)
        self.assertEqual(second.audit_count, 0)

        new_original = list(self.original)
        new_original[0] = replace(
            new_original[0],
            nilai_tahun_berjalan=9999999,
        )
        self.assertIsNone(
            self.store.load_matching(
                "1234567890123456",
                2025,
                new_original,
            )
        )


if __name__ == "__main__":
    unittest.main()
