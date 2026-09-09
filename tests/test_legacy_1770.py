import sys
from pathlib import Path

import pytest
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from config.database import init_database
from core.evy_reconciliation import EvyReconciliationResult
from core.finalization import FinalizationInput, FinalizationService
from core.legacy_1770 import Legacy1770DocumentService
from core.legacy_pdf_exporter import Legacy1770PdfExporter
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow


app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "legacy1770.db"
    init_database(path)
    return path


def _analysis():
    return EvyReconciliationResult(
        total_harta_sebelumnya=10_000_000.0,
        total_harta_berjalan=15_000_000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=5_000_000.0,
        biaya_hidup_setahun=19_200_000.0,
        pajak_pajak=1_000_000.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=25_200_000.0,
        penghasilan_bruto_umkm=600_000_000.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=100_000_000.0,
        jumlah_penghasilan_bukan_objek=50_000_000.0,
        penghasilan_netto=25_200_000.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )


def _input():
    return FinalizationInput(
        npwp="1234567890123456",
        nama_wp="Budi Santoso",
        tahun_pajak=2025,
        harta_current_rows=[
            WorksheetHartaRow(
                nomor=1,
                kode_eform="011",
                kode_ct="0101",
                nama_harta="Uang Tunai",
                nomor_akun_keterangan="",
                atas_nama="Budi Santoso",
                nama_bank="",
                tahun_perolehan=2020,
                nilai_tahun_sebelumnya=10_000_000.0,
                nilai_tahun_berjalan=15_000_000.0,
            )
        ],
        harta_original_hash="hash-original",
        bupot_rows=[
            WorksheetBupotRow(
                jenis="PPh Pasal 21",
                npwp_pemberi_kerja="123456789012345",
                no_bupot="BP-001",
                bruto=100_000_000.0,
                pengurang=5_000_000.0,
            )
        ],
        pph_components={"status_ptkp": "TK/0"},
        umkm_state={
            "bruto_bulanan": [50_000_000.0] * 12,
            "pph_setor_bulanan": [250_000.0] * 12,
        },
        penghasilan_lainnya={
            "domestic_other_dpp": 10_000_000.0,
            "prive_dpp": 0.0,
            "hibah_warisan_dpp": 50_000_000.0,
            "final_other_rows": [
                {"keterangan": "Bunga Deposito", "dpp": 100_000_000.0, "tarif": 0.20}
            ],
        },
        zakat=5_000_000.0,
        status_ptkp="TK/0",
        pph_calc_result={
            "total_netto_bupot": 95_000_000.0,
            "penghasilan_neto_lainnya": 10_000_000.0,
            "pengurang_penghasilan_neto": 5_000_000.0,
            "penghasilan_neto_gabungan": 100_000_000.0,
            "ptkp": 54_000_000.0,
            "pkp": 46_000_000.0,
            "pph_terutang": 2_300_000.0,
            "kredit_pajak": 1_000_000.0,
            "pph25": 500_000.0,
            "kurang_lebih_bayar_pembulatan": 800_000.0,
        },
        analisis_result=_analysis(),
    )


def _finalize(db_path):
    result = FinalizationService(db_path=db_path).finalize(_input())
    assert result.success is True
    return result


def test_document_built_from_active_final(db_path):
    _finalize(db_path)
    document = Legacy1770DocumentService(db_path=db_path).build_active_final(
        "1234567890123456", 2025
    )

    assert document.can_export_pdf is True
    assert document.nama_wp == "Budi Santoso"
    assert document.revision == 1
    assert document.status_ptkp == "TK/0"
    assert document.pph_terutang == 2_300_000.0
    assert document.kurang_lebih_bayar == 800_000.0
    assert len(document.harta_rows) == 1
    assert document.harta_rows[0].kode_eform == "011"
    assert document.harta_rows[0].nilai_tahun_berjalan == 15_000_000.0


def test_document_preserves_known_gaps_as_warnings(db_path):
    _finalize(db_path)
    document = Legacy1770DocumentService(db_path=db_path).build_active_final(
        "1234567890123456", 2025
    )
    codes = {issue.code for issue in document.warnings}
    assert "PDF_W01" in codes
    assert "PDF_W02" in codes


def test_missing_final_blocks_document(db_path):
    document = Legacy1770DocumentService(db_path=db_path).build_active_final(
        "1234567890123456", 2025
    )
    assert document.can_export_pdf is False
    assert any(issue.code == "PDF_001" for issue in document.errors)


def test_pdf_export_creates_five_page_pdf(db_path, tmp_path):
    _finalize(db_path)
    document = Legacy1770DocumentService(db_path=db_path).build_active_final(
        "1234567890123456", 2025
    )
    target = tmp_path / "format_lama_1770.pdf"
    result = Legacy1770PdfExporter().export(document, target)

    assert result == target
    assert target.exists()
    assert target.read_bytes().startswith(b"%PDF")
    assert target.stat().st_size > 5_000

    pdf = QPdfDocument()
    assert pdf.load(str(target)) == QPdfDocument.Error.None_
    assert pdf.pageCount() == 5


def test_pdf_export_rejects_unfinalized_document(db_path, tmp_path):
    document = Legacy1770DocumentService(db_path=db_path).build_active_final(
        "1234567890123456", 2025
    )
    with pytest.raises(ValueError):
        Legacy1770PdfExporter().export(document, tmp_path / "blocked.pdf")
