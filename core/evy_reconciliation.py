from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# Mengikuti tabel biaya hidup pada sheet 2025 kertas kerja EVY BACHTIAR.
# Dasar biaya hidup = Rp 1.600.000 / orang / bulan.
LIVING_COST_PEOPLE_BY_PTKP: Dict[str, int] = {
    "TK/0": 1,
    "TK/1": 2,
    "TK/2": 3,
    "TK/3": 4,
    "K/0": 2,
    "K/1": 3,
    "K/2": 4,
    "K/3": 5,
    "K/I/0": 1,
    "K/I/1": 2,
    "K/I/2": 3,
    "K/I/3": 4,
}

MONTHLY_LIVING_COST_PER_PERSON = 1_600_000.0


@dataclass(frozen=True)
class EvyReconciliationResult:
    total_harta_sebelumnya: float
    total_harta_berjalan: float
    total_utang_sebelumnya: float
    total_utang_berjalan: float
    naik_turun_harta_utang: float
    biaya_hidup_setahun: float
    pajak_pajak: float
    pengeluaran_lain_lain: float
    kerugian_keuntungan_penjualan_aset: float
    utang_baru_atas_kredit: float
    harta_baru_dari_kredit: float
    total_pengeluaran: float
    penghasilan_bruto_umkm: float
    penambahan_penghasilan_bruto_umkm: float
    margin_usaha: float
    jumlah_penghasilan_bruto_final: float
    jumlah_penghasilan_bukan_objek: float
    penghasilan_netto: float
    selisih_pengeluaran_vs_penghasilan: float


def living_cost_for_ptkp(status_ptkp: str) -> float:
    status = str(status_ptkp or "TK/0").strip().upper().replace(" ", "")
    people = LIVING_COST_PEOPLE_BY_PTKP.get(status, 1)
    return float(people) * MONTHLY_LIVING_COST_PER_PERSON * 12.0


def calculate_evy_reconciliation(
    *,
    total_harta_sebelumnya: float,
    total_harta_berjalan: float,
    total_utang_sebelumnya: float = 0.0,
    total_utang_berjalan: float = 0.0,
    status_ptkp: str = "TK/0",
    # Pajak-pajak mengikuti J58 pada SIMULASI I Evy.
    pph_umkm_setor: float = 0.0,
    pph21_terutang: float = 0.0,
    sewa_pph: float = 0.0,
    honor_pph: float = 0.0,
    final_other_pph_subtotal: float = 0.0,
    final_other_pph_detail: float = 0.0,
    pekerjaan_bebas_pph: float = 0.0,
    # Komponen pengeluaran manual pada blok ANALISIS.
    pengeluaran_lain_lain: float = 0.0,
    kerugian_keuntungan_penjualan_aset: float = 0.0,
    utang_baru_atas_kredit: float = 0.0,
    harta_baru_dari_kredit: float = 0.0,
    # Komponen penghasilan.
    penghasilan_bruto_umkm: float = 0.0,
    penambahan_penghasilan_bruto_umkm: float = 0.0,
    margin_usaha: float = 0.0,
    netto_bupot: float = 0.0,
    domestic_other: float = 0.0,
    pekerjaan_bebas_dpp: float = 0.0,
    prive_dpp: float = 0.0,
    hibah_warisan_dpp: float = 0.0,
    sewa_dpp: float = 0.0,
    honor_dpp: float = 0.0,
    final_other_dpp: float = 0.0,
) -> EvyReconciliationResult:
    harta_prev = float(total_harta_sebelumnya)
    harta_now = float(total_harta_berjalan)
    utang_prev = float(total_utang_sebelumnya)
    utang_now = float(total_utang_berjalan)

    # SIMULASI I!J56 = J47-I47-(J53-I53)
    naik_turun = (harta_now - harta_prev) - (utang_now - utang_prev)
    biaya_hidup = living_cost_for_ptkp(status_ptkp)

    # SIMULASI I!J58 = '2025'!G50 + '2025'!F78 + SUM('2025'!G54:G60)
    # Kertas kerja Evy menjumlahkan subtotal PPh Final Lainnya dan baris detailnya;
    # engine mempertahankan perilaku tersebut agar hasil rekonsiliasi identik.
    pajak_pajak = (
        float(pph_umkm_setor)
        + float(pph21_terutang)
        + float(sewa_pph)
        + float(honor_pph)
        + float(final_other_pph_subtotal)
        + float(final_other_pph_detail)
        + float(pekerjaan_bebas_pph)
    )

    total_pengeluaran = (
        naik_turun
        + biaya_hidup
        + pajak_pajak
        + float(pengeluaran_lain_lain)
        + float(kerugian_keuntungan_penjualan_aset)
        + float(utang_baru_atas_kredit)
        - float(harta_baru_dari_kredit)
    )

    umkm = float(penghasilan_bruto_umkm)
    tambahan_umkm = float(penambahan_penghasilan_bruto_umkm)
    margin = float(margin_usaha)

    # SIMULASI I!J11 = Sewa + Bruto UMKM + Honor + Penghasilan Final Lainnya.
    jumlah_bruto_final = (
        float(sewa_dpp) + umkm + float(honor_dpp) + float(final_other_dpp)
    )
    # SIMULASI I!J18 pada data Evy = Prive + Hibah/Warisan.
    jumlah_bukan_objek = float(prive_dpp) + float(hibah_warisan_dpp)

    # SIMULASI I!J68 = SUM(J65:J66)*J67 + SUM(J12:J14,J18) + J11 - J8
    penghasilan_netto = (
        (umkm + tambahan_umkm) * margin
        + float(netto_bupot)
        + float(domestic_other)
        + float(pekerjaan_bebas_dpp)
        + jumlah_bukan_objek
        + jumlah_bruto_final
        - umkm
    )

    # SIMULASI I!J70 = J68-J63
    selisih = penghasilan_netto - total_pengeluaran

    return EvyReconciliationResult(
        total_harta_sebelumnya=harta_prev,
        total_harta_berjalan=harta_now,
        total_utang_sebelumnya=utang_prev,
        total_utang_berjalan=utang_now,
        naik_turun_harta_utang=naik_turun,
        biaya_hidup_setahun=biaya_hidup,
        pajak_pajak=pajak_pajak,
        pengeluaran_lain_lain=float(pengeluaran_lain_lain),
        kerugian_keuntungan_penjualan_aset=float(kerugian_keuntungan_penjualan_aset),
        utang_baru_atas_kredit=float(utang_baru_atas_kredit),
        harta_baru_dari_kredit=float(harta_baru_dari_kredit),
        total_pengeluaran=total_pengeluaran,
        penghasilan_bruto_umkm=umkm,
        penambahan_penghasilan_bruto_umkm=tambahan_umkm,
        margin_usaha=margin,
        jumlah_penghasilan_bruto_final=jumlah_bruto_final,
        jumlah_penghasilan_bukan_objek=jumlah_bukan_objek,
        penghasilan_netto=penghasilan_netto,
        selisih_pengeluaran_vs_penghasilan=selisih,
    )
