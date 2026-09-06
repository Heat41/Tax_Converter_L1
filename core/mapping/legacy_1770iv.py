from dataclasses import dataclass
from typing import Iterable, List, Optional

from config.constants import KategoriL1
from core.models.asset import HartaL1Item


@dataclass(frozen=True)
class Legacy1770IVRow:
    """Canonical row for the legacy 1770-IV asset table.

    This model is deliberately independent from Excel coordinates. Stage 3D
    converts the unified HartaL1Item model into these stable legacy columns;
    the template writer can be implemented later without changing tax data
    mapping rules.
    """

    kode_harta: str
    nama_harta: str
    tahun_perolehan: int
    harga_perolehan: float
    keterangan: str = ""
    source_category: Optional[str] = None
    source_file: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "Kode Harta": self.kode_harta,
            "Nama Harta": self.nama_harta,
            "Tahun Perolehan": self.tahun_perolehan,
            "Harga Perolehan": self.harga_perolehan,
            "Keterangan": self.keterangan,
        }


class Legacy1770IVMapper:
    """Map unified Coretax L-1 assets to canonical legacy 1770-IV rows."""

    def map_item(self, item: HartaL1Item) -> Legacy1770IVRow:
        return Legacy1770IVRow(
            kode_harta=str(item.kode_harta or "").strip(),
            nama_harta=self._build_asset_name(item),
            tahun_perolehan=int(item.tahun_perolehan),
            harga_perolehan=float(item.get_effective_acquisition_cost()),
            keterangan=self._build_remarks(item),
            source_category=item.source_category,
            source_file=item.source_file,
        )

    def map_items(
        self,
        items: Iterable[HartaL1Item],
        *,
        include_inactive: bool = False,
    ) -> List[Legacy1770IVRow]:
        rows: List[Legacy1770IVRow] = []
        for item in items:
            if not include_inactive and not bool(item.is_active):
                continue
            rows.append(self.map_item(item))
        return rows

    @staticmethod
    def total_acquisition_cost(rows: Iterable[Legacy1770IVRow]) -> float:
        return float(sum(row.harga_perolehan for row in rows))

    @staticmethod
    def _join(parts: Iterable[object], separator: str = " - ") -> str:
        clean = [str(value).strip() for value in parts if value is not None and str(value).strip()]
        return separator.join(clean)

    def _build_asset_name(self, item: HartaL1Item) -> str:
        if item.kategori_l1 == KategoriL1.KAS:
            name = self._join((item.nama_bank_institusi, item.nomor_akun))
            return name or "Kas / Setara Kas"

        if item.kategori_l1 == KategoriL1.PIUTANG:
            counterparty = item.nama_pihak_ketiga or item.nomor_identitas_pihak_ketiga
            return f"Piutang kepada {counterparty}" if counterparty else "Piutang"

        if item.kategori_l1 == KategoriL1.INVESTASI:
            name = self._join((item.nama_institusi, item.nomor_akun_bukti))
            return name or "Investasi"

        if item.kategori_l1 == KategoriL1.BERGERAK:
            name = self._join((item.merek_model, item.nomor_polisi_registrasi))
            return name or "Harta Bergerak"

        if item.kategori_l1 == KategoriL1.HTB:
            return item.lokasi_alamat or "Harta Tidak Bergerak"

        if item.kategori_l1 == KategoriL1.LAINNYA:
            return item.informasi_tambahan or item.nomor_akun_bukti or "Harta Lainnya"

        return "Harta"

    def _build_remarks(self, item: HartaL1Item) -> str:
        details: List[str] = []

        if item.kategori_l1 == KategoriL1.KAS:
            if item.atas_nama:
                details.append(f"Atas nama: {item.atas_nama}")
            if item.lokasi_negara:
                details.append(f"Lokasi: {item.lokasi_negara}")

        elif item.kategori_l1 == KategoriL1.PIUTANG:
            if item.nomor_identitas_pihak_ketiga:
                details.append(f"Identitas: {item.nomor_identitas_pihak_ketiga}")
            if item.nilai_piutang_current:
                details.append(f"Nilai piutang: {item.nilai_piutang_current:g}")
            if item.lokasi_negara:
                details.append(f"Lokasi: {item.lokasi_negara}")

        elif item.kategori_l1 == KategoriL1.INVESTASI:
            if item.nilai_saat_ini_current:
                details.append(f"Nilai saat ini: {item.nilai_saat_ini_current:g}")
            if item.lokasi_negara:
                details.append(f"Lokasi: {item.lokasi_negara}")

        elif item.kategori_l1 == KategoriL1.BERGERAK:
            if item.nama_pemilik:
                details.append(f"Pemilik: {item.nama_pemilik}")
            if item.npwp_pemilik:
                details.append(f"NPWP pemilik: {item.npwp_pemilik}")
            if item.jenis_kepemilikan:
                details.append(f"Kepemilikan: {item.jenis_kepemilikan.value}")
            if item.nilai_saat_ini_current:
                details.append(f"Nilai saat ini: {item.nilai_saat_ini_current:g}")

        elif item.kategori_l1 == KategoriL1.HTB:
            if item.luas_tanah:
                details.append(f"Luas tanah: {item.luas_tanah}")
            if item.luas_bangunan:
                details.append(f"Luas bangunan: {item.luas_bangunan}")
            if item.nomor_sertifikat:
                details.append(f"Sertifikat: {item.nomor_sertifikat}")
            if item.sumber_kepemilikan:
                details.append(f"Sumber: {item.sumber_kepemilikan}")
            if item.nilai_saat_ini_current:
                details.append(f"Nilai saat ini: {item.nilai_saat_ini_current:g}")

        elif item.kategori_l1 == KategoriL1.LAINNYA:
            if item.nomor_akun_bukti:
                details.append(f"Bukti/Nomor akun: {item.nomor_akun_bukti}")
            if item.nilai_saat_ini_current:
                details.append(f"Nilai saat ini: {item.nilai_saat_ini_current:g}")

        if item.keterangan_pps:
            details.append(f"PPS: {item.keterangan_pps}")
        if item.keterangan_tambahan:
            details.append(item.keterangan_tambahan)

        return self._join(details, separator="; ")
