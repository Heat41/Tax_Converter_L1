from core.coretax_official_schema import (
    OFFICIAL_CORETAX_SCHEMAS,
    get_official_schema,
)


def test_all_six_l1_categories_have_official_excel_schema():
    assert set(OFFICIAL_CORETAX_SCHEMAS) == {
        "KAS", "PIUTANG", "INVESTASI", "BERGERAK", "HTB", "LAINNYA"
    }
    assert all(schema.excel_sheet == "DATA" for schema in OFFICIAL_CORETAX_SCHEMAS.values())
    assert all(schema.excel_headers for schema in OFFICIAL_CORETAX_SCHEMAS.values())


def test_four_uploaded_xml_references_are_locked():
    assert get_official_schema("KAS").xml_root == "CashAndCashEquivalentBulk"
    assert get_official_schema("INVESTASI").xml_root == "InvesmentSecuritiesBulk"
    assert get_official_schema("BERGERAK").xml_root == "MovableAssetsBulk"
    assert get_official_schema("HTB").xml_root == "NonMovableAssetsBulk"


def test_piutang_and_lainnya_xml_stay_unclaimed_without_reference():
    assert get_official_schema("PIUTANG").has_xml_reference is False
    assert get_official_schema("LAINNYA").has_xml_reference is False
