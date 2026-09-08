from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FinalOtherIncomeRow:
    keterangan: str = ""
    dpp: float = 0.0
    tarif: float = 0.0

    @property
    def pph(self) -> float:
        return max(0.0, float(self.dpp)) * max(0.0, float(self.tarif))


@dataclass(frozen=True)
class FinalOtherIncomeSummary:
    rows: tuple[FinalOtherIncomeRow, ...]
    total_dpp: float
    total_pph: float


def calculate_final_other_income(
    rows: Iterable[FinalOtherIncomeRow],
) -> FinalOtherIncomeSummary:
    normalized = tuple(
        FinalOtherIncomeRow(
            keterangan=" ".join(str(row.keterangan or "").strip().split()),
            dpp=max(0.0, float(row.dpp or 0)),
            tarif=max(0.0, float(row.tarif or 0)),
        )
        for row in rows
    )
    return FinalOtherIncomeSummary(
        rows=normalized,
        total_dpp=sum(row.dpp for row in normalized),
        total_pph=sum(row.pph for row in normalized),
    )


def default_evy_final_other_income_rows() -> list[FinalOtherIncomeRow]:
    """Baris awal mengikuti struktur detail pada kertas kerja EVY BACHTIAR.

    Nama dapat diubah dari UI. Tarif awal mengikuti formula pada workbook Evy:
    deposito 20% dan obligasi 10%.
    """
    return [
        FinalOtherIncomeRow("Deposito 1", 0.0, 0.20),
        FinalOtherIncomeRow("Deposito 2", 0.0, 0.20),
        FinalOtherIncomeRow("Obligasi", 0.0, 0.10),
    ]
