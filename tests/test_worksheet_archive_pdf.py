from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from core.finalization import FinalizationInput
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_archive_exporter_styled import StyledWorksheetArchiveExporter


class _Analysis:
    total_pengeluaran = 100.0
    penghasilan_netto = 100.0
    selisih_pengeluaran_vs_penghasilan = 0.0


def _input():
    return FinalizationInput(
        npwp="6101015612710001",
        nama_wp="WP PDF TEST",
        tahun_pajak=2025,
        harta_current_rows=[
            WorksheetHartaRow(
                nomor=1,
                kode_eform="014",
                kode_ct="0104",
                nama_harta="Deposito",
                nomor_akun_keterangan="123",
                atas_nama="WP PDF TEST",
                nama_bank="BANK TEST",
                tahun_perolehan=2024,
                nilai_tahun_sebelumnya=100.0,
                nilai_tahun_berjalan=125.0,
            )
        ],
        harta_original_hash="hash",
        bupot_rows=[],
        pph_components={"ptkp": 54_000_000, "kredit_pajak": 0, "pph25": 0},
        umkm_state={},
        penghasilan_lainnya={},
        zakat=0.0,
        status_ptkp="TK/0",
        pph_calc_result={"pph_terutang": 0},
        analisis_result=_Analysis(),
    )


def test_export_pdf_archive(tmp_path: Path):
    app = QGuiApplication.instance()
    owns_app = app is None
    if app is None:
        app = QGuiApplication([sys.argv[0]])
    try:
        path = tmp_path / "arsip.pdf"
        result = StyledWorksheetArchiveExporter().export_pdf(_input(), path)
        assert result.output_path == path
        assert path.exists()
        assert path.stat().st_size > 1000
        assert path.read_bytes().startswith(b"%PDF")
    finally:
        if owns_app:
            app.quit()
