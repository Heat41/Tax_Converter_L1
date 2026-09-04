from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from config.constants import KategoriL1, JenisKepemilikan

@dataclass
class HartaL1Item:
    wp_id: int
    kategori_l1: KategoriL1
    kode_harta: str
    tahun_perolehan: int

    # KAS & SETARA KAS
    nomor_akun: Optional[str] = None
    atas_nama: Optional[str] = None
    nama_bank_institusi: Optional[str] = None
    lokasi_negara: Optional[str] = None
    saldo_original: float = 0.0
    saldo_current: float = 0.0

    # PIUTANG
    nomor_identitas_pihak_ketiga: Optional[str] = None
    nama_pihak_ketiga: Optional[str] = None
    nilai_piutang_original: float = 0.0
    nilai_piutang_current: float = 0.0
    saldo_piutang_original: float = 0.0
    saldo_piutang_current: float = 0.0

    # INVESTASI
    nama_institusi: Optional[str] = None
    nomor_akun_bukti: Optional[str] = None
    biaya_perolehan_original: float = 0.0
    biaya_perolehan_current: float = 0.0
    nilai_saat_ini_original: float = 0.0
    nilai_saat_ini_current: float = 0.0

    # HARTA BERGERAK
    merek_model: Optional[str] = None
    nomor_polisi_registrasi: Optional[str] = None
    jenis_kepemilikan: Optional[JenisKepemilikan] = None
    npwp_pemilik: Optional[str] = None
    nama_pemilik: Optional[str] = None

    # HARTA TIDAK BERGERAK
    lokasi_alamat: Optional[str] = None
    luas_tanah: Optional[str] = None
    luas_bangunan: Optional[str] = None
    sumber_kepemilikan: Optional[str] = None
    nomor_sertifikat: Optional[str] = None

    # HARTA LAINNYA
    informasi_tambahan: Optional[str] = None

    # METADATA & STATUS
    keterangan_pps: Optional[str] = None
    keterangan_tambahan: Optional[str] = None
    source_file: Optional[str] = None
    source_category: Optional[str] = None
    is_edited: int = 0
    is_active: int = 1
    import_batch_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.kategori_l1, str):
            self.kategori_l1 = KategoriL1(self.kategori_l1)
        if isinstance(self.jenis_kepemilikan, str) and self.jenis_kepemilikan:
            self.jenis_kepemilikan = JenisKepemilikan(self.jenis_kepemilikan)

    def get_effective_acquisition_cost(self) -> float:
        """Mengembalikan nilai perolehan / saldo aktif untuk pelaporan SPT."""
        if self.kategori_l1 == KategoriL1.KAS:
            return self.saldo_current
        elif self.kategori_l1 == KategoriL1.PIUTANG:
            return self.saldo_piutang_current
        else:
            return self.biaya_perolehan_current

    def get_original_acquisition_cost(self) -> float:
        """Mengembalikan nilai asli perolehan Coretax yang immutable."""
        if self.kategori_l1 == KategoriL1.KAS:
            return self.saldo_original
        elif self.kategori_l1 == KategoriL1.PIUTANG:
            return self.saldo_piutang_original
        else:
            return self.biaya_perolehan_original
