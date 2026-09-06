from dataclasses import dataclass
from typing import Iterable, List, Optional

from config.constants import KategoriL1
from core.models.asset import HartaL1Item
from core.mapping.eform_reference import find_eform_reference


@dataclass(frozen=True)
class WorksheetHartaRow:
    nomor: int
    kode_eform: str
    kode_ct: str
    nama_harta: str
    nomor_akun_keterangan: str
    atas_nama: str
    nama_bank: str
    tahun_perolehan: int
    nilai_tahun_sebelumnya: float
    nilai_tahun_berjalan: float


class WorksheetHartaMapper:
    """Adapter Stage 3F untuk tabel harta pada sheet SIMULASI I.

    Struktur mengikuti workbook acuan nyata:
    NO | KODE EFORM | KODE CT | NAMA HARTA | NOMOR AKUN/KETERANGAN |
    ATAS NAMA | NAMA BANK | TH PEROLEHAN | tahun sebelumnya | tahun berjalan
    """

    def map_items(
        self,
        current_items: Iterable[HartaL1Item],
        *,
        previous_items: Optional[Iterable[HartaL1Item]] = None,
    ) -> List[WorksheetHartaRow]:
        previous_index = {
            self._match_key(item): item
            for item in (previous_items or [])
            if item.is_active
        }

        rows: List[WorksheetHartaRow] = []
        for item in current_items:
            if not item.is_active:
                continue

            ref = find_eform_reference(
                item.kode_harta,
                description_hint=self._description_hint(item),
            )
            if ref is None:
                raise ValueError(
                    f"Kode CT '{item.kode_harta}' belum memiliki mapping Kode EFORM."
                )

            previous = previous_index.get(self._match_key(item))
            rows.append(
                WorksheetHartaRow(
                    nomor=len(rows) + 1,
                    kode_eform=ref.kode_eform,
                    kode_ct=str(item.kode_harta).strip(),
                    nama_harta=ref.nama_harta,
                    nomor_akun_keterangan=self._account_or_remark(item),
                    atas_nama=self._owner_name(item),
                    nama_bank=self._bank_name(item),
                    tahun_perolehan=int(item.tahun_perolehan),
                    nilai_tahun_sebelumnya=(
                        float(previous.get_effective_acquisition_cost())
                        if previous is not None
                        else 0.0
                    ),
                    nilai_tahun_berjalan=float(item.get_effective_acquisition_cost()),
                )
            )

        return rows

    @staticmethod
    def _match_key(item: HartaL1Item) -> tuple:
        identity = (
            item.nomor_akun
            or item.nomor_akun_bukti
            or item.nomor_polisi_registrasi
            or item.nomor_sertifikat
            or item.nomor_identitas_pihak_ketiga
            or item.lokasi_alamat
            or item.informasi_tambahan
            or item.merek_model
            or item.nama_bank_institusi
            or item.nama_institusi
            or item.nama_pihak_ketiga
            or ""
        )
        return (str(item.kode_harta).strip(), str(identity).strip().lower())

    @staticmethod
    def _description_hint(item: HartaL1Item) -> str:
        return " ".join(
            str(value)
            for value in (
                item.merek_model,
                item.informasi_tambahan,
                item.keterangan_tambahan,
                item.keterangan_pps,
            )
            if value
        )

    @staticmethod
    def _account_or_remark(item: HartaL1Item) -> str:
        if item.kategori_l1 == KategoriL1.KAS:
            return item.nomor_akun or item.keterangan_tambahan or "-"
        if item.kategori_l1 == KategoriL1.PIUTANG:
            return item.nomor_identitas_pihak_ketiga or item.keterangan_tambahan or "-"
        if item.kategori_l1 == KategoriL1.INVESTASI:
            return item.nomor_akun_bukti or item.keterangan_tambahan or "-"
        if item.kategori_l1 == KategoriL1.BERGERAK:
            return item.nomor_polisi_registrasi or item.merek_model or item.keterangan_tambahan or "-"
        if item.kategori_l1 == KategoriL1.HTB:
            details = [value for value in (item.nomor_sertifikat, item.lokasi_alamat) if value]
            return "; ".join(details) if details else "-"
        return item.nomor_akun_bukti or item.informasi_tambahan or item.keterangan_tambahan or "-"

    @staticmethod
    def _owner_name(item: HartaL1Item) -> str:
        if item.kategori_l1 == KategoriL1.KAS:
            return item.atas_nama or "-"
        if item.kategori_l1 == KategoriL1.PIUTANG:
            return item.nama_pihak_ketiga or "-"
        if item.kategori_l1 == KategoriL1.INVESTASI:
            return item.nama_institusi or "-"
        if item.kategori_l1 == KategoriL1.BERGERAK:
            return item.nama_pemilik or "-"
        return "-"

    @staticmethod
    def _bank_name(item: HartaL1Item) -> str:
        if item.kategori_l1 == KategoriL1.KAS:
            return item.nama_bank_institusi or "-"
        return "-"
