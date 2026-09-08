from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Dict, Tuple


PTKP_BY_STATUS: Dict[str, float] = {
    "TK/0": 54_000_000.0,
    "TK/1": 58_500_000.0,
    "TK/2": 63_000_000.0,
    "TK/3": 67_500_000.0,
    "K/0": 58_500_000.0,
    "K/1": 63_000_000.0,
    "K/2": 67_500_000.0,
    "K/3": 72_000_000.0,
    "K/I/0": 112_500_000.0,
    "K/I/1": 117_000_000.0,
    "K/I/2": 121_500_000.0,
    "K/I/3": 126_000_000.0,
}

# Batas progresif yang dipakai pada sheet 2025 kertas kerja EVY BACHTIAR.
PPh_BRACKETS: Tuple[Tuple[float | None, float], ...] = (
    (60_000_000.0, 0.05),
    (250_000_000.0, 0.15),
    (500_000_000.0, 0.25),
    (5_000_000_000.0, 0.30),
    (None, 0.35),
)


@dataclass(frozen=True)
class AnnualPPhResult:
    total_netto_bupot: float
    penghasilan_neto_lainnya: float
    pengurang_penghasilan_neto: float
    penghasilan_neto_sebelum_pengurang: float
    penghasilan_neto_gabungan: float
    status_ptkp: str
    ptkp: float
    pkp: float
    pph_terutang: float
    kredit_pajak: float
    pph25: float
    kurang_lebih_bayar: float
    kurang_lebih_bayar_pembulatan: float


def normalize_ptkp_status(value: object) -> str:
    status = str(value or "TK/0").strip().upper().replace(" ", "")
    if status not in PTKP_BY_STATUS:
        raise ValueError(f"Status PTKP tidak dikenal: {value}")
    return status


def ptkp_value(status: object) -> float:
    return PTKP_BY_STATUS[normalize_ptkp_status(status)]


def round_down_thousand(value: float) -> float:
    """Setara ROUNDDOWN(value,-3) untuk nilai penghasilan non-negatif."""
    decimal_value = Decimal(str(float(value)))
    if decimal_value >= 0:
        return float((decimal_value / Decimal("1000")).to_integral_value(rounding=ROUND_DOWN) * Decimal("1000"))
    # Jaga perilaku menuju nol untuk nilai negatif, sama dengan ROUNDDOWN Excel.
    return float((decimal_value / Decimal("1000")).to_integral_value(rounding=ROUND_DOWN) * Decimal("1000"))


def excel_round(value: float, digits: int = 0) -> float:
    """Pembulatan half-away-from-zero yang konsisten dengan ROUND Excel."""
    quantum = Decimal("1").scaleb(-digits)
    return float(Decimal(str(float(value))).quantize(quantum, rounding=ROUND_HALF_UP))


def progressive_pph(pkp: float) -> float:
    taxable = max(0.0, float(pkp))
    lower = 0.0
    tax = 0.0

    for upper, rate in PPh_BRACKETS:
        if upper is None:
            layer = max(0.0, taxable - lower)
        else:
            layer = max(0.0, min(taxable, upper) - lower)
        tax += layer * rate

        if upper is None or taxable <= upper:
            break
        lower = upper

    return excel_round(tax, 0)


def calculate_annual_pph(
    *,
    total_netto_bupot: float,
    penghasilan_neto_lainnya: float = 0.0,
    pengurang_penghasilan_neto: float = 0.0,
    status_ptkp: str = "TK/0",
    kredit_pajak: float = 0.0,
    pph25: float = 0.0,
) -> AnnualPPhResult:
    status = normalize_ptkp_status(status_ptkp)
    ptkp = ptkp_value(status)

    # Acuan EVY sheet 2025:
    # F73 = ROUNDDOWN(H34 + F53, -3) - F64
    # H34 = Total NETTO Bupot, F53 = Penghasilan Dalam Negeri Lainnya,
    # F64 = Zakat/Pengurang Penghasilan Neto.
    neto_sebelum_pengurang = round_down_thousand(
        float(total_netto_bupot) + float(penghasilan_neto_lainnya)
    )
    neto_gabungan = neto_sebelum_pengurang - float(pengurang_penghasilan_neto)
    pkp = max(0.0, neto_gabungan - ptkp)
    pph_terutang = progressive_pph(pkp)
    kurang_lebih = pph_terutang - float(kredit_pajak) - float(pph25)

    # Acuan EVY membulatkan nilai akhir dengan ROUND(...,-2).
    kurang_lebih_rounded = excel_round(kurang_lebih, -2)

    return AnnualPPhResult(
        total_netto_bupot=float(total_netto_bupot),
        penghasilan_neto_lainnya=float(penghasilan_neto_lainnya),
        pengurang_penghasilan_neto=float(pengurang_penghasilan_neto),
        penghasilan_neto_sebelum_pengurang=neto_sebelum_pengurang,
        penghasilan_neto_gabungan=neto_gabungan,
        status_ptkp=status,
        ptkp=ptkp,
        pkp=pkp,
        pph_terutang=pph_terutang,
        kredit_pajak=float(kredit_pajak),
        pph25=float(pph25),
        kurang_lebih_bayar=kurang_lebih,
        kurang_lebih_bayar_pembulatan=kurang_lebih_rounded,
    )
