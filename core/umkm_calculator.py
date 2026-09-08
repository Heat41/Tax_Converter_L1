from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Sequence


UMKM_FREE_THRESHOLD = 500_000_000.0
UMKM_FINAL_RATE = 0.005
UMKM_MONTHS = (
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)


@dataclass(frozen=True)
class UMKMMonthResult:
    nomor: int
    masa: str
    bruto: float
    kumulatif_bruto: float
    pph: float
    pph_setor: float
    selisih: float


@dataclass(frozen=True)
class UMKMAnnualResult:
    months: tuple[UMKMMonthResult, ...]
    total_bruto: float
    total_pph: float
    total_pph_setor: float
    total_selisih: float


def excel_round_zero(value: float) -> float:
    """Samakan ROUND(...,0) Excel untuk nilai moneter positif/negatif."""
    return float(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _normalize_12(values: Iterable[float] | None) -> list[float]:
    normalized = [float(value or 0) for value in (values or [])]
    if len(normalized) > 12:
        raise ValueError("Data UMKM maksimal 12 masa pajak.")
    normalized.extend([0.0] * (12 - len(normalized)))
    if any(value < 0 for value in normalized):
        raise ValueError("Nilai UMKM tidak boleh negatif.")
    return normalized


def calculate_umkm_monthly(
    bruto_bulanan: Sequence[float] | None,
    pph_setor_bulanan: Sequence[float] | None = None,
) -> UMKMAnnualResult:
    """Hitung PPh Final UMKM mengikuti formula sheet 2025 milik Evy.

    Formula Excel per masa:
    ROUND(MAX(0, bruto_kumulatif - 500.000.000) * 0,5%
          - PPh_masa_sebelumnya, 0)
    """
    bruto_values = _normalize_12(bruto_bulanan)
    setor_values = _normalize_12(pph_setor_bulanan)

    cumulative_bruto = 0.0
    prior_pph = 0.0
    results: list[UMKMMonthResult] = []

    for index, (bruto, pph_setor) in enumerate(zip(bruto_values, setor_values)):
        cumulative_bruto += bruto
        raw_month_pph = (
            max(0.0, cumulative_bruto - UMKM_FREE_THRESHOLD) * UMKM_FINAL_RATE
            - prior_pph
        )
        pph = max(0.0, excel_round_zero(raw_month_pph))
        prior_pph += pph
        selisih = pph - pph_setor
        results.append(
            UMKMMonthResult(
                nomor=index + 1,
                masa=UMKM_MONTHS[index],
                bruto=bruto,
                kumulatif_bruto=cumulative_bruto,
                pph=pph,
                pph_setor=pph_setor,
                selisih=selisih,
            )
        )

    return UMKMAnnualResult(
        months=tuple(results),
        total_bruto=sum(item.bruto for item in results),
        total_pph=sum(item.pph for item in results),
        total_pph_setor=sum(item.pph_setor for item in results),
        total_selisih=sum(item.selisih for item in results),
    )
