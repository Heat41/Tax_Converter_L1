from core.legacy_1770_multipage_final import (
    Legacy1770MultipageService,
    MultipagePageSummary,
)


def test_non_last_page_displays_only_page_subtotal():
    summary = MultipagePageSummary(
        section="L1",
        page_number=2,
        page_count=4,
        subtotal=57_232_543,
        grand_total=788_920_417,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 57_232_543


def test_section_page_helper_distinguishes_last_page():
    assert Legacy1770MultipageService._is_last_section_page(3, 4) is False
    assert Legacy1770MultipageService._is_last_section_page(4, 4) is True
    assert Legacy1770MultipageService._is_last_section_page(5, 4) is True


def test_last_page_displays_only_grand_total():
    summary = MultipagePageSummary(
        section="L1",
        page_number=4,
        page_count=4,
        subtotal=120_000_000,
        grand_total=788_920_417,
        subtotal_available=True,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 788_920_417


def test_non_last_page_without_reconciled_detail_displays_dash():
    summary = MultipagePageSummary(
        section="L2",
        page_number=1,
        page_count=2,
        subtotal=None,
        grand_total=105_486_376,
        subtotal_available=False,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) is None


def test_last_page_uses_grand_total_even_when_detail_is_unavailable():
    summary = MultipagePageSummary(
        section="L2",
        page_number=2,
        page_count=2,
        subtotal=None,
        grand_total=105_486_376,
        subtotal_available=False,
    )

    assert Legacy1770MultipageService._display_value_for_summary(summary) == 105_486_376
