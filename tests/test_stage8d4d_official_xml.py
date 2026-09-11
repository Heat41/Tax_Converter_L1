from xml.etree import ElementTree as ET

from core.reverse_coretax_mapping import ReverseCoretaxPackage, ReverseCoretaxRow
from core.reverse_coretax_official_xml import (
    XML_CATEGORY_ORDER,
    OfficialCoretaxXmlExporter,
)


def _row(category, code, metadata):
    return ReverseCoretaxRow(
        nomor=1,
        kategori=category,
        kode_harta=code,
        nama_harta="",
        tahun_perolehan=2025,
        nilai=1000,
        nomor_akun_keterangan="",
        atas_nama="",
        nama_bank="",
        official_metadata=metadata,
    )


def _package():
    package = ReverseCoretaxPackage(
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
        revision=1,
    )

    package.rows_by_category["KAS"].append(
        _row(
            "KAS",
            "0102",
            {
                "account_number": "116801005138508",
                "account_on_behalf_of": "DR EVY BACHTIAR SPOG",
                "bank_name": "BRI",
                "country": "Indonesia",
                "year": 2025,
                "balance": 391742658,
            },
        )
    )

    package.rows_by_category["INVESTASI"].append(
        _row(
            "INVESTASI",
            "0305",
            {
                "country": "Indonesia",
                "institution_tin": "6101015612710001",
                "institution_name": "EVY BACHTIAR",
                "account_number": "1971197117",
                "cost_of_acquisition": 1000000000,
                "year": 2025,
                "current_balance": 1000000000,
                "remarks": "Investasi",
            },
        )
    )

    package.rows_by_category["BERGERAK"].append(
        _row(
            "BERGERAK",
            "0403",
            {
                "asset_model": "TOYOTA RAIZE",
                "police_registration_number": "KB 1476 PI",
                "ownership_type": "TAXPAYER",
                "ownership_tin": "6101015612710001",
                "ownership_name": "EVY BACHTIAR",
                "year": 2025,
                "cost_of_acquisition": 343750000,
                "fair_market_value": 325000000,
            },
        )
    )

    package.rows_by_category["HTB"].append(
        _row(
            "HTB",
            "0501",
            {
                "location_of_asset": "JAGUR KAB SAMBAS",
                "property_size_land": "607 M2",
                "property_size_building": "-",
                "source_of_ownership": "Own Income",
                "certificate_number": "14030604100666",
                "year": 2021,
                "cost_of_acquisition": 35000000,
                "fair_market_value": 38000000,
            },
        )
    )

    return package


def test_stage8d4d_only_exports_categories_with_official_xml_reference(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)

    assert result.ok
    assert tuple(result.files) == XML_CATEGORY_ORDER
    assert set(result.files) == {"KAS", "INVESTASI", "BERGERAK", "HTB"}
    assert result.unsupported_categories == []


def test_stage8d4d_cash_xml_matches_locked_contract(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["KAS"]).getroot()

    assert root.tag == "CashAndCashEquivalentBulk"
    rows = root.findall("CashAndCashEquivalentList")
    assert len(rows) == 1

    row = rows[0]
    assert [child.tag for child in row] == [
        "Code",
        "AccountNumber",
        "AccountOnBehalfOf",
        "BankName",
        "Country",
        "Year",
        "Balance",
    ]
    assert row.findtext("Code") == "0102"
    assert row.findtext("AccountNumber") == "116801005138508"
    assert row.findtext("Balance") == "391742658"


def test_stage8d4d_investment_keeps_official_spelling_and_fields(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["INVESTASI"]).getroot()

    assert root.tag == "InvesmentSecuritiesBulk"
    row = root.find("InvesmentSecuritiesList")
    assert row is not None
    assert row.findtext("BankTIN") == "6101015612710001"
    assert row.findtext("AccountNumber") == "1971197117"
    assert row.findtext("CurrentBalance") == "1000000000"
    assert row.findtext("Remarks") == "Investasi"


def test_stage8d4d_movable_xml_uses_preserved_metadata(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["BERGERAK"]).getroot()
    row = root.find("MovableAssetsList")

    assert root.tag == "MovableAssetsBulk"
    assert row is not None
    assert row.findtext("AssetModel") == "TOYOTA RAIZE"
    assert row.findtext("PoliceRegistrationNumber") == "KB 1476 PI"
    assert row.findtext("OwnershipTIN") == "6101015612710001"
    assert row.findtext("FairMarketValue") == "325000000"


def test_stage8d4d_non_movable_xml_uses_preserved_metadata(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["HTB"]).getroot()
    row = root.find("NonMovableAssetsList")

    assert root.tag == "NonMovableAssetsBulk"
    assert row is not None
    assert row.findtext("LocationOfAsset") == "JAGUR KAB SAMBAS"
    assert row.findtext("PropertySizeLand") == "607 M2"
    assert row.findtext("CertificateNumber") == "14030604100666"
    assert row.findtext("FairMarketValue") == "38000000"


def test_stage8d4d_does_not_generate_empty_supported_categories(tmp_path):
    package = ReverseCoretaxPackage(
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
    )
    package.rows_by_category["KAS"].append(
        _row(
            "KAS",
            "0101",
            {
                "account_number": "001",
                "account_on_behalf_of": "EVY",
                "bank_name": "BANK",
                "country": "Indonesia",
                "year": 2025,
                "balance": 1,
            },
        )
    )

    result = OfficialCoretaxXmlExporter().export_package(package, tmp_path)

    assert set(result.files) == {"KAS"}
    assert "INVESTASI" not in result.files
