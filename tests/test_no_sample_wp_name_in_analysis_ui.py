from pathlib import Path


def test_analysis_ui_does_not_expose_sample_wp_name():
    source = Path("ui/pages/worksheet_pph_stage7.py").read_text(encoding="utf-8")

    assert "EVY BACHTIAR" not in source
    assert "kertas kerja aktif" in source
