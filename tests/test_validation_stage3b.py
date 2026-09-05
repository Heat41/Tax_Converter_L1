from pathlib import Path

from core.validation.batch import CoretaxBatchImporter
from core.validation.engine import ValidationEngine


def test_partial_categories_are_allowed():
    importer = CoretaxBatchImporter()
    files = [Path("1. PIT L1 Harta Kas Setara Kas 250918.xlsx")]
    result = importer.classify_files(files)
    assert result.found_count == 1
    assert "KAS SETARA KAS" in result.category_files
    assert not result.errors
    assert len(result.missing_categories) == 5


def test_tidak_bergerak_precedes_bergerak():
    importer = CoretaxBatchImporter()
    assert importer.detect_category(Path("PIT L1 Harta Tidak Bergerak 250918.xlsx")) == "HARTA TIDAK BERGERAK"
    assert importer.detect_category(Path("PIT L1 Harta Bergerak 250918.xlsx")) == "HARTA BERGERAK"


def test_duplicate_category_is_error():
    importer = CoretaxBatchImporter()
    files = [Path("PIT L1 Harta Piutang 1.xlsx"), Path("PIT L1 Harta Piutang 2.xlsx")]
    result = importer.classify_files(files)
    assert "PIUTANG" in result.duplicate_categories
    assert any(issue.code == "DUPLICATE_CATEGORY" for issue in result.errors)


def test_invalid_required_npwp_and_positive_number():
    engine = ValidationEngine()
    headers = ["NPWP*", "TAHUN PAJAK*", "KODE*", "NOMOR AKUN*", "ATAS NAMA*", "NAMA BANK/ INSTITUSI*", "LOKASI HARTA*", "TAHUN PEROLEHAN*", "SALDO*"]
    rows = [["123", "2025", "0101", "123", "DAVID", "MANDIRI", "Indonesia", "2025", "-10"]]
    result = engine.validate_rows("KAS SETARA KAS", headers, rows)
    codes = {issue.code for issue in result.errors}
    assert "INVALID_NPWP" in codes
    assert "INVALID_POSITIVE_NUMBER" in codes
    assert not result.is_valid


def test_empty_reference_set_does_not_reject_code():
    engine = ValidationEngine()
    headers = ["NPWP*", "TAHUN PAJAK*", "KODE*"]
    rows = [["1234567890123456", "2025", "9999"]]
    result = engine.validate_rows("KAS SETARA KAS", headers, rows)
    assert not any(issue.code == "INVALID_REFERENCE" for issue in result.errors)
