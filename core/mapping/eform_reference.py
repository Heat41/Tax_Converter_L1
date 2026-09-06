from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class EFormAssetReference:
    kode_eform: str
    kode_ct: str
    nama_harta: str

    @property
    def ct_codes(self) -> List[str]:
        return [part.strip() for part in self.kode_ct.split("/") if part.strip()]


# Disalin dari sheet REF pada kertas kerja acuan yang menghasilkan format lama DJP.
EFORM_ASSET_REFERENCES: tuple[EFormAssetReference, ...] = (
    EFormAssetReference("011", "0101", "Uang Tunai/Bank Note/Koin"),
    EFormAssetReference("012", "0102", "Tabungan (Bank/Lembaga Keuangan)"),
    EFormAssetReference("013", "0103", "Giro"),
    EFormAssetReference("014", "0104", "Deposito"),
    EFormAssetReference("019", "0712/0799", "Setara Kas Lainnya"),
    EFormAssetReference("021", "0201", "Piutang"),
    EFormAssetReference("022", "0202", "Piutang Afiliasi"),
    EFormAssetReference("029", "0209", "Piutang Lainnya"),
    EFormAssetReference("031", "0301", "Saham yang Dibeli untuk Dijual Kembali"),
    EFormAssetReference("032", "0302", "Saham"),
    EFormAssetReference("033", "0304", "Obligasi Perusahaan"),
    EFormAssetReference("034", "0305", "Obligasi Pemerintah Indonesia"),
    EFormAssetReference("035", "0306", "Surat Utang Lainnya"),
    EFormAssetReference("036", "0307", "Reksadana"),
    EFormAssetReference("037", "0308", "Instrumen Derivatif"),
    EFormAssetReference("038", "0309", "Penyertaan Modal Non Saham"),
    EFormAssetReference("039", "0399", "Investasi Lainnya"),
    EFormAssetReference("041", "0401", "Sepeda"),
    EFormAssetReference("042", "0402", "Sepeda Motor"),
    EFormAssetReference("043", "0403", "Mobil"),
    EFormAssetReference("049", "0499", "Alat Transportasi Lainnya"),
    EFormAssetReference("051", "0701/0702", "Logam Mulia"),
    EFormAssetReference("052", "0705", "Batu Mulia"),
    EFormAssetReference("053", "0706", "Barang Seni dan Antik"),
    EFormAssetReference("054", "0707", "Kapal/Pesawat/Helikopter/Peralatan Khusus"),
    EFormAssetReference("055", "0708/0709", "Peralatan Elektronik/Furnitur"),
    EFormAssetReference("059", "0499", "Harta Bergerak Lainnya"),
    EFormAssetReference("061", "0501/0502", "Tanah dan/atau Bangunan Tempat Tinggal"),
    EFormAssetReference("062", "0506", "Tanah dan/atau Bangunan untuk Usaha"),
    EFormAssetReference("063", "0505", "Tanah/Lahan untuk Usaha"),
    EFormAssetReference("069", "0509", "Harta Tidak Bergerak Lainnya"),
    EFormAssetReference("071", "0601", "Paten"),
    EFormAssetReference("072", "0602", "Royalti"),
    EFormAssetReference("073", "0603", "Merek Dagang"),
    EFormAssetReference("079", "0699", "Harta Tidak Berwujud Lainnya"),
)


def find_eform_reference(
    kode_ct: str,
    *,
    description_hint: Optional[str] = None,
) -> Optional[EFormAssetReference]:
    code = str(kode_ct or "").strip()
    matches = [ref for ref in EFORM_ASSET_REFERENCES if code in ref.ct_codes]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    # REF memiliki satu kode CT ambigu (0499). Gunakan deskripsi bila tersedia.
    hint = (description_hint or "").strip().lower()
    if hint:
        if any(word in hint for word in ("transport", "kendaraan", "mobil", "motor", "sepeda")):
            for ref in matches:
                if ref.kode_eform == "049":
                    return ref
        for ref in matches:
            if ref.kode_eform == "059":
                return ref

    # Fallback konservatif: harta bergerak lainnya.
    return next((ref for ref in matches if ref.kode_eform == "059"), matches[0])
