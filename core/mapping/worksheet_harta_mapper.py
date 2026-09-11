from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

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
    # Metadata Coretax resmi tidak ditampilkan sebagai kolom worksheet ringkas,
    # tetapi ikut berjalan sampai snapshot FINAL untuk reverse-export.
    coretax_metadata: Dict[str, object] = field(default_factory=dict)


class WorksheetHartaMapper:
    """Adapter Stage 3F untuk tabel harta pada sheet SIMULASI I.

    Struktur visual mengikuti workbook acuan:
    NO | KODE EFORM | KODE CT | NAMA HARTA | NOMOR AKUN/KETERANGAN |
    ATAS NAMA | NAMA BANK | TH PEROLEHAN | tahun sebelumnya | tahun berjalan

    Stage 8D.4B menambahkan coretax_metadata sebagai payload tersembunyi agar
    field resmi Coretax yang tidak tampil di tabel ringkas tidak hilang ketika
    data diteruskan ke Worksheet dan snapshot FINAL.
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
                    coretax_metadata=self._coretax_metadata(item),
                )
            )

        return rows

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        if hasattr(value, "value"):
            return value.value
        return value

    @classmethod
    def _coretax_metadata(cls, item: HartaL1Item) -> Dict[str, object]:
        """Simpan field detail Coretax dengan nama netral dan stabil.

        Nilai ini bukan tebakan untuk field yang tidak tersedia. Field kosong
        dibiarkan kosong agar exporter resmi dapat memberi warning/error yang
        tepat daripada membuat data palsu.
        """
        common = {
            "category": item.kategori_l1.value,
            "code": str(item.kode_harta or "").strip(),
            "year": int(item.tahun_perolehan or 0),
            "remarks": str(item.keterangan_tambahan or "").strip(),
            "source_file": str(item.source_file or "").strip(),
            "source_category": str(item.source_category or "").strip(),
        }

        if item.kategori_l1 == KategoriL1.KAS:
            common.update({
                "account_number": cls._clean(item.nomor_akun),
                "account_on_behalf_of": cls._clean(item.atas_nama),
                "bank_name": cls._clean(item.nama_bank_institusi),
                "country": cls._clean(item.lokasi_negara),
                "balance": float(item.saldo_current or 0),
                "balance_original": float(item.saldo_original or 0),
            })
        elif item.kategori_l1 == KategoriL1.PIUTANG:
            common.update({
                "country": cls._clean(item.lokasi_negara),
                "identity_number": cls._clean(item.nomor_identitas_pihak_ketiga),
                "receivable_name": cls._clean(item.nama_pihak_ketiga),
                "receivable_value": float(item.nilai_piutang_current or 0),
                "receivable_value_original": float(item.nilai_piutang_original or 0),
                "receivable_balance": float(item.saldo_piutang_current or 0),
                "receivable_balance_original": float(item.saldo_piutang_original or 0),
            })
        elif item.kategori_l1 == KategoriL1.INVESTASI:
            common.update({
                "country": cls._clean(item.lokasi_negara),
                "institution_tin": cls._clean(item.nomor_identitas_institusi),
                "institution_name": cls._clean(item.nama_institusi),
                "account_number": cls._clean(item.nomor_akun_bukti),
                "cost_of_acquisition": float(item.biaya_perolehan_current or 0),
                "cost_of_acquisition_original": float(item.biaya_perolehan_original or 0),
                "current_balance": float(item.nilai_saat_ini_current or 0),
                "current_balance_original": float(item.nilai_saat_ini_original or 0),
            })
        elif item.kategori_l1 == KategoriL1.BERGERAK:
            common.update({
                "asset_model": cls._clean(item.merek_model),
                "police_registration_number": cls._clean(item.nomor_polisi_registrasi),
                "ownership_type": cls._clean(item.jenis_kepemilikan),
                "ownership_tin": cls._clean(item.npwp_pemilik),
                "ownership_name": cls._clean(item.nama_pemilik),
                "cost_of_acquisition": float(item.biaya_perolehan_current or 0),
                "cost_of_acquisition_original": float(item.biaya_perolehan_original or 0),
                "fair_market_value": float(item.nilai_saat_ini_current or 0),
                "fair_market_value_original": float(item.nilai_saat_ini_original or 0),
            })
        elif item.kategori_l1 == KategoriL1.HTB:
            common.update({
                "location_of_asset": cls._clean(item.lokasi_alamat),
                "property_size_land": cls._clean(item.luas_tanah),
                "property_size_building": cls._clean(item.luas_bangunan),
                "source_of_ownership": cls._clean(item.sumber_kepemilikan),
                "certificate_number": cls._clean(item.nomor_sertifikat),
                "cost_of_acquisition": float(item.biaya_perolehan_current or 0),
                "cost_of_acquisition_original": float(item.biaya_perolehan_original or 0),
                "fair_market_value": float(item.nilai_saat_ini_current or 0),
                "fair_market_value_original": float(item.nilai_saat_ini_original or 0),
            })
        elif item.kategori_l1 == KategoriL1.LAINNYA:
            common.update({
                "account_number": cls._clean(item.nomor_akun_bukti),
                "additional_information": cls._clean(item.informasi_tambahan),
                "cost_of_acquisition": float(item.biaya_perolehan_current or 0),
                "cost_of_acquisition_original": float(item.biaya_perolehan_original or 0),
                "current_value": float(item.nilai_saat_ini_current or 0),
                "current_value_original": float(item.nilai_saat_ini_original or 0),
            })
        return common

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
