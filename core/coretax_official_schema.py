from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class OfficialCoretaxSchema:
    category: str
    excel_filename_hint: str
    excel_sheet: str
    excel_headers: Tuple[str, ...]
    xml_root: Optional[str] = None
    xml_list: Optional[str] = None
    xml_item: Optional[str] = None
    xml_tin_field: str = "TIN"
    xml_year_field: str = "TaxPeriodYear"
    xml_fields: Tuple[str, ...] = ()

    @property
    def has_xml_reference(self) -> bool:
        return bool(
            self.xml_root
            and self.xml_list
            and self.xml_item
            and self.xml_fields
        )


OFFICIAL_CORETAX_SCHEMAS: Dict[str, OfficialCoretaxSchema] = {
    "KAS": OfficialCoretaxSchema(
        category="KAS",
        excel_filename_hint="PIT L1 Harta Kas Setara Kas",
        excel_sheet="DATA",
        excel_headers=(
            "KODE*",
            "NOMOR AKUN*",
            "ATAS NAMA*",
            "NAMA BANK/ INSTITUSI*",
            "LOKASI HARTA*",
            "TAHUN PEROLEHAN*",
            "SALDO*",
            "KETERANGAN",
        ),
        xml_root="CashAndCashEquivalentBulk",
        xml_list="CashAndCashEquivalentList",
        xml_item="List",
        xml_fields=(
            "Code",
            "AccountNumber",
            "AccountOnBehalfOf",
            "BankName",
            "Country",
            "Year",
            "Balance",
        ),
    ),
    "PIUTANG": OfficialCoretaxSchema(
        category="PIUTANG",
        excel_filename_hint="PIT L1 Harta Piutang",
        excel_sheet="DATA",
        excel_headers=(
            "Kode Harta",
            "Negara Lokasi",
            "Nomor Identitas",
            "Nama Penerima Piutang",
            "Nilai Piutang",
            "Tahun",
            "Saldo Piutang",
            "Keterangan",
        ),
    ),
    "INVESTASI": OfficialCoretaxSchema(
        category="INVESTASI",
        excel_filename_hint="PIT L1 Harta Investasi",
        excel_sheet="DATA",
        excel_headers=(
            "Kode *",
            "Lokasi Harta *",
            "Nomor Identitas *",
            "Nama Bank/Institusi/Penerima Investasi *",
            "Bukti Kepemilikan/Nomor Akun *",
            "Biaya Perolehan *",
            "Tahun Perolehan *",
            "Nilai Saat Ini *",
            "Keterangan",
        ),
        xml_root="InvesmentSecuritiesBulk",
        xml_list="InvesmentSecuritiesList",
        xml_item="List",
        xml_fields=(
            "Code",
            "Country",
            "BankTIN",
            "BankName",
            "AccountNumber",
            "CostOfAcquisition",
            "Year",
            "CurrentBalance",
            "Remarks",
        ),
    ),
    "BERGERAK": OfficialCoretaxSchema(
        category="BERGERAK",
        excel_filename_hint="PIT L1 Harta Bergerak",
        excel_sheet="DATA",
        excel_headers=(
            "Kode *",
            "Merk/Model *",
            "Nomor Polisi/Registrasi *",
            "Kepemilikan*",
            "NPWP Pemilik*",
            "Nama Pemilik *",
            "Tahun Perolehan *",
            "Biaya Perolehan *",
            "Nilai Saat Ini *",
            "Keterangan",
        ),
        xml_root="MovableAssetsBulk",
        xml_list="MovableAssetsList",
        xml_item="List",
        xml_fields=(
            "Code",
            "AssetModel",
            "PoliceRegistrationNumber",
            "OwnershipType",
            "OwnershipTIN",
            "OwnershipName",
            "Year",
            "CostOfAcquisition",
            "FairMarketValue",
        ),
    ),
    "HTB": OfficialCoretaxSchema(
        category="HTB",
        excel_filename_hint="PIT L1 Harta Tidak Bergerak",
        excel_sheet="DATA",
        excel_headers=(
            "Kode *",
            "Lokasi Harta *",
            "Ukuran Properti - Tanah *",
            "Ukuran Properti - Bangunan *",
            "Sumber Kepemilikan *",
            "Nomor Sertifikat *",
            "Tahun Perolehan *",
            "Biaya Perolehan *",
            "Nilai Saat Ini *",
            "Keterangan",
        ),
        xml_root="NonMovableAssetsBulk",
        xml_list="NonMovableAssetsList",
        xml_item="List",
        xml_fields=(
            "Code",
            "LocationOfAsset",
            "PropertySizeLand",
            "PropertySizeBuilding",
            "SourceOfOwnership",
            "CertificateNumber",
            "Year",
            "CostOfAcquisition",
            "FairMarketValue",
        ),
    ),
    "LAINNYA": OfficialCoretaxSchema(
        category="LAINNYA",
        excel_filename_hint="PIT L1 Harta Lainnya",
        excel_sheet="DATA",
        excel_headers=(
            "Kode *",
            "Tahun Perolehan *",
            "Bukti Kepemilikan/Nomor Akun *",
            "Informasi Tambahan *",
            "Biaya Perolehan *",
            "Nilai Saat Ini *",
            "Keterangan",
        ),
    ),
}


def get_official_schema(category: str) -> OfficialCoretaxSchema:
    key = str(category or "").strip().upper()
    if key not in OFFICIAL_CORETAX_SCHEMAS:
        raise KeyError(f"Kategori Coretax resmi tidak dikenal: {category}")
    return OFFICIAL_CORETAX_SCHEMAS[key]
