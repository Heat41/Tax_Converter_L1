from typing import Dict, List

from .models import CoretaxFieldRule


CATEGORIES = [
    "KAS SETARA KAS",
    "PIUTANG",
    "INVESTASI",
    "HARTA BERGERAK",
    "HARTA TIDAK BERGERAK",
    "LAINNYA",
]


# Rules are derived from the Coretax workbook field specifications inspected
# in Stage 3A. Reference lists are intentionally injectable; the workbook's
# REF sheets can be wired in later without changing the validation engine.
RULES: Dict[str, List[CoretaxFieldRule]] = {
    "KAS SETARA KAS": [
        CoretaxFieldRule("KAS SETARA KAS", "NPWP*", "TIN", True, "npwp", ["required", "npwp16"], raw_validation="16 digit angka NPWP valid"),
        CoretaxFieldRule("KAS SETARA KAS", "TAHUN PAJAK*", "TaxYear", True, "year", ["required", "digits4"] , raw_validation="4 digit angka"),
        CoretaxFieldRule("KAS SETARA KAS", "KODE*", "Code", True, "code", ["required", "digits4", "reference"], "KAS", "4 digit angka sesuai kode referensi Harta Kas dan Setara Kas"),
        CoretaxFieldRule("KAS SETARA KAS", "NOMOR AKUN*", "AccountNumber", True, "text", ["required"]),
        CoretaxFieldRule("KAS SETARA KAS", "ATAS NAMA*", "AccountOnBehalfOf", True, "text", ["required"]),
        CoretaxFieldRule("KAS SETARA KAS", "NAMA BANK/ INSTITUSI*", "BankName", True, "text", ["required"]),
        CoretaxFieldRule("KAS SETARA KAS", "LOKASI HARTA*", "Country", True, "country", ["required", "reference"], "COUNTRY", "sesuai Code Description referensi Country Code"),
        CoretaxFieldRule("KAS SETARA KAS", "TAHUN PEROLEHAN*", "Year", True, "year", ["required", "digits4"] , raw_validation="4 digit angka"),
        CoretaxFieldRule("KAS SETARA KAS", "SALDO*", "Balance", True, "positive", ["required", "positive"] , raw_validation="angka positif"),
        CoretaxFieldRule("KAS SETARA KAS", "KETERANGAN", "Remarks", False, "remark", ["optional", "remark"], "REMARK", "2 digit angka sesuai kode referensi Remark atau kosong"),
    ],
    "PIUTANG": [
        CoretaxFieldRule("PIUTANG", "NPWP *", "TIN", True, "npwp", ["required", "npwp16"], raw_validation="16 digit angka NPWP sesuai SPT yang dilaporkan"),
        CoretaxFieldRule("PIUTANG", "Tahun Pajak *", "TaxPeriodYear", True, "year", ["required", "digits4"], raw_validation="4 digit angka sesuai tahun pajak SPT yang dilaporkan"),
        CoretaxFieldRule("PIUTANG", "Kode Harta *", "Code", True, "code", ["required", "digits4", "reference"], "PIUTANG", "4 digit angka sesuai referensi Account Receivable Assets"),
        CoretaxFieldRule("PIUTANG", "Negara Lokasi *", "Country", True, "country", ["required", "reference"], "COUNTRY", "sesuai Code Description referensi Country Code"),
        CoretaxFieldRule("PIUTANG", "Nomor Identitas *", "TinNikRecipient", True, "text", ["required"]),
        CoretaxFieldRule("PIUTANG", "Nama Penerima *", "RecipientOfReceivable", True, "text", ["required"]),
        CoretaxFieldRule("PIUTANG", "Nilai Piutang *", "ReceivableValue", True, "positive", ["required", "positive"], raw_validation="angka positif"),
        CoretaxFieldRule("PIUTANG", "Tahun *", "Year", True, "year", ["required", "digits4"], raw_validation="4 digit angka, maksimal sama dengan tahun SPT yang dilaporkan"),
        CoretaxFieldRule("PIUTANG", "Saldo Piutang *", "CurrentBalance", True, "positive", ["required", "positive"], raw_validation="angka positif"),
        CoretaxFieldRule("PIUTANG", "Keterangan", "Remarks", False, "remark", ["optional", "remark"], "REMARK", "2 digit angka sesuai kode referensi Remark atau kosong"),
    ],
    "INVESTASI": [
        CoretaxFieldRule("INVESTASI", "NPWP*", "TIN", True, "npwp", ["required", "npwp16"]),
        CoretaxFieldRule("INVESTASI", "TAHUN PAJAK*", "TaxYear", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("INVESTASI", "Kode *", "Code", True, "code", ["required", "digits4", "reference"], "INVESTASI"),
        CoretaxFieldRule("INVESTASI", "Lokasi Harta *", "Country", True, "country", ["required", "reference"], "COUNTRY"),
        CoretaxFieldRule("INVESTASI", "Nomor Identitas *", "TINRecipient", True, "text", ["required"]),
        CoretaxFieldRule("INVESTASI", "Nama Bank/Institusi/Penerima Investasi *", "NameRecipient", True, "text", ["required"]),
        CoretaxFieldRule("INVESTASI", "Bukti Kepemilikan/Nomor Akun *", "AccountNumber", True, "text", ["required"]),
        CoretaxFieldRule("INVESTASI", "Biaya Perolehan *", "CostOfAcquisition", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("INVESTASI", "Tahun Perolehan *", "Year", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("INVESTASI", "Nilai Saat Ini *", "CurrentBalance", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("INVESTASI", "Keterangan", "Remarks", False, "remark", ["optional", "remark"], "REMARK"),
    ],
    "HARTA BERGERAK": [
        CoretaxFieldRule("HARTA BERGERAK", "NPWP*", "TIN", True, "npwp", ["required", "npwp16"]),
        CoretaxFieldRule("HARTA BERGERAK", "TAHUN PAJAK *", "TaxYear", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("HARTA BERGERAK", "Kode *", "Code", True, "code", ["required", "digits4", "reference"], "BERGERAK"),
        CoretaxFieldRule("HARTA BERGERAK", "Merk/Model *", "AssetModel", True, "text", ["required"]),
        CoretaxFieldRule("HARTA BERGERAK", "Nomor Polisi/Registrasi *", "PoliceRegistrationNumber", True, "text", ["required"]),
        CoretaxFieldRule("HARTA BERGERAK", "Kepemilikan*", "OwnershipType", True, "text", ["required", "reference"], "OWNERSHIP_MOVEABLE_ASSET"),
        CoretaxFieldRule("HARTA BERGERAK", "NPWP Pemilik*", "OwnershipTIN", True, "text", ["required"]),
        CoretaxFieldRule("HARTA BERGERAK", "Nama Pemotong Pajak *", "OwnershipName", True, "text", ["required"]),
        CoretaxFieldRule("HARTA BERGERAK", "Tahun Perolehan *", "Year", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("HARTA BERGERAK", "Biaya Perolehan *", "CostOfAcquisition", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("HARTA BERGERAK", "Nilai Saat Ini *", "FairMarketValue", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("HARTA BERGERAK", "Keterangan", "Remarks", False, "remark", ["optional", "remark"], "REMARK"),
    ],
    "HARTA TIDAK BERGERAK": [
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "NPWP*", "TIN", True, "npwp", ["required", "npwp16"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "TAHUN PAJAK *", "TaxYear", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Kode *", "Code", True, "code", ["required", "digits4", "reference"], "TIDAK_BERGERAK"),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Lokasi Harta *", "LocationOfAsset", True, "text", ["required"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Ukuran Properti - Tanah *", "PropertySizeLand", True, "text", ["required"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Ukuran Properti - Bangunan *", "PropertySizeBuilding", True, "text", ["required"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Sumber Kepemilikan *", "SourceOfOwnership", True, "text", ["required", "reference"], "SOURCE_OF_INCOME"),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Nomor Sertifikat *", "CertificateNumber", True, "text", ["required"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Tahun Perolehan *", "Year", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Biaya Perolehan *", "CostOfAcquisition", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Nilai Saat Ini *", "FairMarketValue", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("HARTA TIDAK BERGERAK", "Keterangan", "Remarks", False, "remark", ["optional", "remark"], "REMARK"),
    ],
    "LAINNYA": [
        CoretaxFieldRule("LAINNYA", "NPWP*", "TIN", True, "npwp", ["required", "npwp16"]),
        CoretaxFieldRule("LAINNYA", "TAHUN PAJAK *", "TaxYear", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("LAINNYA", "Kode *", "Code", True, "code", ["required", "digits4", "reference"], "LAINNYA"),
        CoretaxFieldRule("LAINNYA", "Tahun Perolehan *", "Year", True, "year", ["required", "digits4"]),
        CoretaxFieldRule("LAINNYA", "Bukti Kepemilikan/Nomor Akun *", "ProofOfOwnership", True, "text", ["required"]),
        CoretaxFieldRule("LAINNYA", "Informasi Tambahan *", "AdditionalInformation", True, "text", ["required"]),
        CoretaxFieldRule("LAINNYA", "Biaya Perolehan *", "CostOfAcquisition", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("LAINNYA", "Nilai Saat Ini *", "FairMarketValue", True, "positive", ["required", "positive"]),
        CoretaxFieldRule("LAINNYA", "Keterangan", "Remarks", False, "remark", ["optional", "remark"], "REMARK"),
    ],
}


def get_rules(category: str) -> List[CoretaxFieldRule]:
    return list(RULES.get(category, []))
