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


def test_all_six_uploaded_xml_references_are_locked():
    assert get_official_schema("KAS").xml_root == "CashAndCashEquivalentBulk"
    assert get_official_schema("INVESTASI").xml_root == "InvesmentSecuritiesBulk"
    assert get_official_schema("BERGERAK").xml_root == "MovableAssetsBulk"
    assert get_official_schema("HTB").xml_root == "NonMovableAssetsBulk"
    assert get_official_schema("PIUTANG").xml_root == "AccountReceivablesBulk"
    assert get_official_schema("LAINNYA").xml_root == "OtherAssetsBulk"
    assert all(schema.has_xml_reference for schema in OFFICIAL_CORETAX_SCHEMAS.values())
