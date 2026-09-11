from pathlib import Path

from openpyxl import Workbook

from config.database import init_database
from core.coretax_official_schema import OFFICIAL_CORETAX_SCHEMAS
from core.evy_reconciliation import EvyReconciliationResult
from core.finalization import FinalizationInput, FinalizationService
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.real_wp_preflight import (
    RealWpPreflightService,
    list_final_snapshots,
)


def _analysis():
    return EvyReconciliationResult(
        total_harta_sebelumnya=0.0,
        total_harta_berjalan=100_000_000.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=100_000_000.0,
        biaya_hidup_setahun=0.0,
        pajak_pajak=0.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=0.0,
        penghasilan_bruto_umkm=0.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=0.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=0.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )


def _final_input():
    return FinalizationInput(
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
        harta_current_rows=[
            WorksheetHartaRow(
                nomor=1,
                kode_eform="061",
                kode_ct="0501",
                nama_harta="Tanah",
                nomor_akun_keterangan="SHM-001; Pontianak",
                atas_nama="-",
                nama_bank="-",
                tahun_perolehan=2021,
                nilai_tahun_sebelumnya=0.0,
                nilai_tahun_berjalan=100_000_000.0,
                coretax_metadata={
                    "category": "HTB",
                    "code": "0501",
                    "location_of_asset": "Pontianak",
                    "property_size_land": "120 M2",
                    "property_size_building": "",
                    "source_of_ownership": "Own Income",
                    "certificate_number": "SHM-001",
                    "year": 2021,
                    "fair_market_value": 100_000_000.0,
                },
            )
        ],
        harta_original_hash="source",
        bupot_rows=[],
        pph_components={},
        umkm_state={},
        penghasilan_lainnya={},
        zakat=0.0,
        status_ptkp="TK/0",
        pph_calc_result={},
        analisis_result=_analysis(),
    )


def _template(directory: Path, category: str):
    directory.mkdir(parents=True, exist_ok=True)
    schema = OFFICIAL_CORETAX_SCHEMAS[category]
    path = directory / f"{schema.excel_filename_hint}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = schema.excel_sheet
    for index, header in enumerate(schema.excel_headers, start=1):
        ws.cell(3, index).value = header
    wb.save(path)
    return path


def _finalized_db(tmp_path):
    db_path = tmp_path / "real_wp.db"
    init_database(db_path)
    result = FinalizationService(db_path=db_path).finalize(_final_input())
    assert result.success
    return db_path


def test_stage8d4j_lists_final_snapshots(tmp_path):
    db_path = _finalized_db(tmp_path)

    rows = list_final_snapshots(db_path=db_path)

    assert len(rows) == 1
    assert rows[0]["npwp"] == "6101015612710001"
    assert rows[0]["tahun_pajak"] == 2025
    assert rows[0]["revision"] == 1


def test_stage8d4j_only_requires_template_for_active_category(tmp_path):
    db_path = _finalized_db(tmp_path)
    templates = tmp_path / "templates"
    _template(templates, "HTB")

    result = RealWpPreflightService(
        db_path=db_path,
        template_dir=templates,
    ).inspect(
        "6101015612710001",
        2025,
    )

    assert result.ready
    assert result.active_categories == ["HTB"]
    assert result.category_counts == {"HTB": 1}
    assert set(result.template_files) == {"HTB"}
    assert result.missing_templates == []


def test_stage8d4j_reports_missing_source_metadata_without_fabricating(tmp_path):
    db_path = _finalized_db(tmp_path)
    templates = tmp_path / "templates"
    _template(templates, "HTB")

    result = RealWpPreflightService(
        db_path=db_path,
        template_dir=templates,
    ).inspect(
        "6101015612710001",
        2025,
    )

    assert result.ready
    assert result.missing_metadata["HTB"][1] == [
        "property_size_building",
        "cost_of_acquisition",
    ]
    assert any(
        issue.code == "RCX4J_101"
        and issue.severity == "WARNING"
        for issue in result.issues
    )


def test_stage8d4j_missing_active_template_is_blocking_error(tmp_path):
    db_path = _finalized_db(tmp_path)
    templates = tmp_path / "templates"
    templates.mkdir()

    result = RealWpPreflightService(
        db_path=db_path,
        template_dir=templates,
    ).inspect(
        "6101015612710001",
        2025,
    )

    assert not result.ready
    assert result.missing_templates == ["HTB"]
    assert any(
        issue.code == "RCX4J_001"
        and issue.severity == "ERROR"
        for issue in result.issues
    )
