import unittest
from pathlib import Path

from core.coretax_reader import CoretaxReadResult
from core.pipeline.harta_pipeline import HartaPreviewPipeline
from core.validation.models import BatchImportResult, FileCategoryResult, ValidationResult


class TestHartaPreviewPipelineStage3G(unittest.TestCase):
    def setUp(self):
        self.pipeline = HartaPreviewPipeline()

    @staticmethod
    def _valid_batch():
        headers = [
            "NPWP*",
            "TAHUN PAJAK*",
            "KODE*",
            "NOMOR AKUN*",
            "ATAS NAMA*",
            "NAMA BANK/ INSTITUSI*",
            "LOKASI HARTA*",
            "TAHUN PEROLEHAN*",
            "SALDO*",
            "KETERANGAN",
        ]
        rows = [[
            "0123456789012345",
            "2025",
            "0102",
            "0668222229",
            "LISA VINATALIA",
            "BCA",
            "ID",
            "2020",
            "1521825000",
            "",
        ]]
        read_result = CoretaxReadResult(
            file_path=Path("PIT L1 Harta Kas Setara Kas.xlsx"),
            file_name="PIT L1 Harta Kas Setara Kas.xlsx",
            sheet_name="KAS SETARA KAS",
            headers=headers,
            rows=rows,
            total_rows=1,
            total_columns=len(headers),
        )
        validation = ValidationResult(
            is_valid=True,
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
        )
        category = FileCategoryResult(
            category="KAS SETARA KAS",
            file_path=read_result.file_path,
            status="VALID",
            read_result=read_result,
            validation=validation,
        )
        return BatchImportResult(
            category_results={"KAS SETARA KAS": category},
        )

    def test_pipeline_maps_batch_to_simulasi_preview(self):
        result = self.pipeline.build_from_batch(self._valid_batch(), wp_id=0)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.worksheet_rows), 1)
        row = result.worksheet_rows[0]
        self.assertEqual(row.kode_ct, "0102")
        self.assertEqual(row.kode_eform, "012")
        self.assertEqual(row.nomor_akun_keterangan, "0668222229")
        self.assertEqual(row.atas_nama, "LISA VINATALIA")
        self.assertEqual(row.nama_bank, "BCA")
        self.assertEqual(row.nilai_tahun_berjalan, 1521825000.0)

    def test_pipeline_infers_tax_year(self):
        result = self.pipeline.build_from_batch(self._valid_batch(), wp_id=0)
        self.assertEqual(result.current_year, 2025)

    def test_pipeline_carries_npwp_for_worksheet_state(self):
        result = self.pipeline.build_from_batch(self._valid_batch(), wp_id=0)
        self.assertEqual(result.npwp, "0123456789012345")

    def test_pipeline_infers_consistent_wp_name_from_owner_as_fallback(self):
        result = self.pipeline.build_from_batch(self._valid_batch(), wp_id=0)
        self.assertEqual(result.nama_wp, "LISA VINATALIA")

    def test_pipeline_keeps_previous_year_zero_without_previous_import(self):
        result = self.pipeline.build_from_batch(self._valid_batch(), wp_id=0)
        self.assertEqual(result.worksheet_rows[0].nilai_tahun_sebelumnya, 0.0)


if __name__ == "__main__":
    unittest.main()
