from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import re
from config.constants import StatusProses

@dataclass
class WajibPajak:
    npwp: str
    nama_wp: str
    tahun_pajak: int = 2025
    status_ptkp: str = "TK/0"
    status_proses: StatusProses = StatusProses.BELUM_IMPOR
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        # 1. NPWP Validasi 16 Digit Angka
        clean_npwp = re.sub(r'[^0-9]', '', str(self.npwp))
        if len(clean_npwp) != 16:
            raise ValueError(f"NPWP harus terdiri dari 16 digit angka, diterima: '{self.npwp}' (panjang {len(clean_npwp)})")
        self.npwp = clean_npwp

        # 2. Validasi Nama WP
        if not self.nama_wp or not str(self.nama_wp).strip():
            raise ValueError("Nama Wajib Pajak tidak boleh kosong")
        self.nama_wp = str(self.nama_wp).strip()

        # 3. Validasi Tahun Pajak
        try:
            self.tahun_pajak = int(self.tahun_pajak)
            if self.tahun_pajak < 2000 or self.tahun_pajak > 2100:
                raise ValueError
        except Exception:
            raise ValueError(f"Tahun pajak tidak valid (2000-2100), diterima: {self.tahun_pajak}")

        # 4. Validasi Status Proses
        if isinstance(self.status_proses, str):
            try:
                self.status_proses = StatusProses(self.status_proses)
            except ValueError:
                raise ValueError(f"Status proses tidak valid: {self.status_proses}")
