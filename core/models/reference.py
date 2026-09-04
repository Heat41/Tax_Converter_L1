from dataclasses import dataclass
from typing import Optional
from config.constants import KategoriL1

@dataclass
class ReferenceKodeHarta:
    kode_eform: str
    kode_coretax: str
    nama_harta_lama: str
    nama_harta_coretax: str
    kategori_l1: KategoriL1
    is_primary_mapping: int = 1
    catatan_mapping: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.kategori_l1, str):
            self.kategori_l1 = KategoriL1(self.kategori_l1)
