import inspect

from core.legacy_1770_lampiran_i_finetuned import Legacy1770LampiranIService
from core.legacy_1770_lampiran_ii_finetuned import Legacy1770LampiranIIService
from core import legacy_1770_lampiran_iv as lampiran_iv


def test_lampiran_i_detail_font_targets_12pt():
    assert Legacy1770LampiranIService.C_IDENTITY_FONT_SIZE == 12.0
    source = inspect.getsource(Legacy1770LampiranIService._draw_right)
    assert "size=12.0" in source


def test_lampiran_ii_detail_font_targets_12pt():
    center = inspect.getsource(Legacy1770LampiranIIService._draw_fit_center)
    money = inspect.getsource(Legacy1770LampiranIIService._draw_right_money)
    assert "size=12.0" in center
    assert "size=12.0" in money


def test_lampiran_iv_detail_renderer_uses_12pt_targets():
    source = inspect.getsource(lampiran_iv.Legacy1770LampiranIVService._make_overlay)
    assert source.count("size=12.0") >= 5
