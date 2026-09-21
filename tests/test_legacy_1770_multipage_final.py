from core.legacy_1770_multipage_final import (
    Legacy1770MultipageService,
    MultipagePageSummary,
)


def test_non_last_lampiran_i_page_displays_grand_total():
    summary = MultipagePageSummary(
        section="L1",
        page_number=2,
        page_count=4,
        subtotal=57_232_543,
        grand_total=788_920_417,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 788_920_417


def test_section_page_helper_distinguishes_last_page():
    assert Legacy1770MultipageService._is_last_section_page(3, 4) is False
    assert Legacy1770MultipageService._is_last_section_page(4, 4) is True
    assert Legacy1770MultipageService._is_last_section_page(5, 4) is True


def test_last_lampiran_i_page_displays_same_grand_total():
    summary = MultipagePageSummary(
        section="L1",
        page_number=4,
        page_count=4,
        subtotal=120_000_000,
        grand_total=788_920_417,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 788_920_417


def test_non_last_bupot_page_displays_grand_total_even_without_page_subtotal():
    summary = MultipagePageSummary(
        section="L2",
        page_number=1,
        page_count=2,
        subtotal=None,
        grand_total=105_486_376,
        subtotal_available=False,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 105_486_376


def test_every_bupot_page_uses_same_grand_total():
    first = MultipagePageSummary(
        section="L2",
        page_number=1,
        page_count=2,
        subtotal=40_000_000,
        grand_total=105_486_376,
        subtotal_available=True,
    )
    last = MultipagePageSummary(
        section="L2",
        page_number=2,
        page_count=2,
        subtotal=65_486_376,
        grand_total=105_486_376,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(first) == 105_486_376
    assert Legacy1770MultipageService._display_value_for_summary(last) == 105_486_376


def test_every_harta_page_uses_same_grand_total():
    first = MultipagePageSummary(
        section="L4",
        page_number=1,
        page_count=3,
        subtotal=150_000_000,
        grand_total=725_000_000,
        subtotal_available=True,
    )
    middle = MultipagePageSummary(
        section="L4",
        page_number=2,
        page_count=3,
        subtotal=250_000_000,
        grand_total=725_000_000,
        subtotal_available=True,
    )
    last = MultipagePageSummary(
        section="L4",
        page_number=3,
        page_count=3,
        subtotal=325_000_000,
        grand_total=725_000_000,
        subtotal_available=True,
    )

    expected = 725_000_000
    assert Legacy1770MultipageService._display_value_for_summary(first) == expected
    assert Legacy1770MultipageService._display_value_for_summary(middle) == expected
    assert Legacy1770MultipageService._display_value_for_summary(last) == expected


def test_total_font_default_is_enlarged():
    source = __import__(
        "inspect"
    ).getsource(Legacy1770MultipageService._make_summary_overlay)
    assert "size = 14.0" in source
    assert "while size > 12.0" in source
