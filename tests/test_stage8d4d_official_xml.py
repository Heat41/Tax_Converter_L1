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
        nama_wp="WAJIB PAJAK TEST",
        tahun_pajak=2025,
        revision=1,
    )

    package.rows_by_category["KAS"].append(
        _row(
            "KAS",
            "0102",
            {
                "account_number": "116801005138508",
                "account_on_behalf_of": "DR WAJIB PAJAK TEST SPOG",
                "bank_name": "BRI",
                "country": "Indonesia",
                "year": 2025,
                "balance": 391742658,
            },
        )
    )

    package.rows_by_category["PIUTANG"].append(
        _row(
            "PIUTANG",
            "0202",
            {
                "country": "Belgium",
                "identity_number": "1234abc",
                "receivable_name": "Lukaku",
                "receivable_value": 24056144,
                "year": 2022,
                "receivable_balance": 379485037,
                "remarks": "01",
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
                "institution_name": "WAJIB PAJAK TEST",
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
                "ownership_name": "WAJIB PAJAK TEST",
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

    package.rows_by_category["LAINNYA"].append(
        _row(
            "LAINNYA",
            "0601",
            {
                "year": 2023,
                "account_number": "1000000000000170",
                "additional_information": "Info 1",
                "cost_of_acquisition": 1000000,
                "current_value": 2000000,
                "remarks": "01",
            },
        )
    )

    return package


def test_stage8d4d_only_exports_categories_with_official_xml_reference(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)

    assert result.ok
    assert tuple(result.files) == XML_CATEGORY_ORDER
    assert set(result.files) == {
        "KAS", "PIUTANG", "INVESTASI", "BERGERAK", "HTB", "LAINNYA"
    }
    assert result.unsupported_categories == []


def test_stage8d4d_cash_xml_matches_locked_contract(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["KAS"]).getroot()

    assert root.tag == "CashAndCashEquivalentBulk"
    assert [child.tag for child in root] == [
        "TIN",
        "TaxPeriodYear",
        "CashAndCashEquivalentList",
    ]
    assert root.findtext("TIN") == "6101015612710001"
    assert root.findtext("TaxPeriodYear") == "2025"

    container = root.find("CashAndCashEquivalentList")
    assert container is not None
    rows = container.findall("List")
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
    container = root.find("InvesmentSecuritiesList")
    assert container is not None
    row = container.find("List")
    assert row is not None
    assert row.findtext("BankTIN") == "6101015612710001"
    assert row.findtext("AccountNumber") == "1971197117"
    assert row.findtext("CurrentBalance") == "1000000000"
    assert row.findtext("Remarks") == "Investasi"


def test_stage8d4d_movable_xml_uses_preserved_metadata(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["BERGERAK"]).getroot()
    container = root.find("MovableAssetsList")
    row = container.find("List") if container is not None else None

    assert root.tag == "MovableAssetsBulk"
    assert row is not None
    assert row.findtext("AssetModel") == "TOYOTA RAIZE"
    assert row.findtext("PoliceRegistrationNumber") == "KB 1476 PI"
    assert row.findtext("OwnershipTIN") == "6101015612710001"
    assert row.findtext("FairMarketValue") == "325000000"


def test_stage8d4d_non_movable_xml_uses_preserved_metadata(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["HTB"]).getroot()
    container = root.find("NonMovableAssetsList")
    row = container.find("List") if container is not None else None

    assert root.tag == "NonMovableAssetsBulk"
    assert row is not None
    assert row.findtext("LocationOfAsset") == "JAGUR KAB SAMBAS"
    assert row.findtext("PropertySizeLand") == "607 M2"
    assert row.findtext("CertificateNumber") == "14030604100666"
    assert row.findtext("FairMarketValue") == "38000000"


def test_stage8d4d_generates_all_six_xml_even_when_categories_are_empty(tmp_path):
    package = ReverseCoretaxPackage(
        npwp="6101015612710001",
        nama_wp="WAJIB PAJAK TEST",
        tahun_pajak=2025,
    )
    package.rows_by_category["KAS"].append(
        _row(
            "KAS",
            "0101",
            {
                "account_number": "001",
                "account_on_behalf_of": "TEST WP",
                "bank_name": "BANK",
                "country": "Indonesia",
                "year": 2025,
                "balance": 1,
            },
        )
    )

    result = OfficialCoretaxXmlExporter().export_package(package, tmp_path)

    assert set(result.files) == {
        "KAS", "PIUTANG", "INVESTASI", "BERGERAK", "HTB", "LAINNYA"
    }
    assert result.row_counts["KAS"] == 1
    assert all(
        result.row_counts[category] == 0
        for category in ("PIUTANG", "INVESTASI", "BERGERAK", "HTB", "LAINNYA")
    )


def test_stage8d4d_receivables_xml_matches_official_djp_contract(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["PIUTANG"]).getroot()

    assert root.tag == "AccountReceivablesBulk"
    assert [child.tag for child in root] == [
        "TIN",
        "TaxPeriodYear",
        "AccountReceivablesList",
    ]
    container = root.find("AccountReceivablesList")
    row = container.find("List") if container is not None else None
    assert row is not None
    assert [child.tag for child in row] == [
        "Code",
        "Country",
        "TinNikRecipient",
        "RecipientOfReceivable",
        "ReceivableValue",
        "Year",
        "CurrentBalance",
        "Remarks",
    ]
    assert row.findtext("Code") == "0202"
    assert row.findtext("Country") == "Belgium"
    assert row.findtext("TinNikRecipient") == "1234abc"
    assert row.findtext("CurrentBalance") == "379485037"
    assert row.findtext("Remarks") == "01"


def test_stage8d4d_other_assets_xml_matches_official_djp_contract(tmp_path):
    result = OfficialCoretaxXmlExporter().export_package(_package(), tmp_path)
    root = ET.parse(result.files["LAINNYA"]).getroot()

    assert root.tag == "OtherAssetsBulk"
    assert [child.tag for child in root] == [
        "TIN",
        "TaxPeriodYear",
        "OtherAssetsList",
    ]
    container = root.find("OtherAssetsList")
    row = container.find("List") if container is not None else None
    assert row is not None
    assert [child.tag for child in row] == [
        "Code",
        "Year",
        "ProofOfOwnership",
        "AdditionalInformation",
        "CostOfAcquisition",
        "FairMarketValue",
        "Remarks",
    ]
    assert row.findtext("Code") == "0601"
    assert row.findtext("ProofOfOwnership") == "1000000000000170"
    assert row.findtext("AdditionalInformation") == "Info 1"
    assert row.findtext("FairMarketValue") == "2000000"
    assert row.findtext("Remarks") == "01"
