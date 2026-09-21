from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
import re
from typing import Iterable, List, Tuple


_INDONESIAN_MONTHS = {
    "JAN": 1, "JANUARI": 1,
    "FEB": 2, "FEBRUARI": 2,
    "MAR": 3, "MARET": 3,
    "APR": 4, "APRIL": 4,
    "MEI": 5,
    "JUN": 6, "JUNI": 6,
    "JUL": 7, "JULI": 7,
    "AGU": 8, "AGUSTUS": 8,
    "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OKT": 10, "OKTOBER": 10,
    "NOV": 11, "NOVEMBER": 11,
    "DES": 12, "DESEMBER": 12,
}


def _int(value, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _month(value) -> int:
    text = str(value or "").strip().upper()
    if not text:
        return 0
    numeric = _int(text)
    if 1 <= numeric <= 12:
        return numeric
    compact = re.sub(r"[^A-Z]", "", text)
    return _INDONESIAN_MONTHS.get(compact, 0)


def _date_parts(value) -> Tuple[int, int, int]:
    """Return (year, month, day); zero means component unavailable."""
    if isinstance(value, datetime):
        return value.year, value.month, value.day
    if isinstance(value, date):
        return value.year, value.month, value.day

    text = str(value or "").strip()
    if not text:
        return 0, 0, 0

    # ISO / yyyy-mm-dd / yyyy/mm/dd.
    match = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if match:
        year, month, day = map(int, match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return year, month, day

    # Indonesian/common dd-mm-yyyy, dd/mm/yyyy, dd.mm.yyyy.
    match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b", text)
    if match:
        day, month, year = map(int, match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return year, month, day

    # Textual month: 4 Juni 2025.
    match = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})\b", text)
    if match:
        day = int(match.group(1))
        month = _month(match.group(2))
        year = int(match.group(3))
        if month and 1 <= day <= 31:
            return year, month, day

    # Month-year only: 06-2025 / 06/2025 / Juni 2025.
    match = re.search(r"\b(\d{1,2})[-/.](20\d{2})\b", text)
    if match:
        month, year = map(int, match.groups())
        if 1 <= month <= 12:
            return year, month, 0

    match = re.search(r"\b([A-Za-z]+)\s+(20\d{2})\b", text)
    if match:
        month = _month(match.group(1))
        if month:
            return int(match.group(2)), month, 0

    return 0, 0, 0


def harta_sort_key(row) -> tuple:
    year = _int(getattr(row, "tahun_perolehan", 0))
    # Tahun kosong/invalid ditempatkan setelah data bertahun valid.
    normalized_year = year if year > 0 else 9999
    return (
        normalized_year,
        str(getattr(row, "kode_ct", "") or "").strip(),
        str(getattr(row, "nama_harta", "") or "").strip().casefold(),
    )


def sort_harta_rows(rows: Iterable) -> List:
    ordered = sorted(list(rows or []), key=harta_sort_key)
    result = []
    for nomor, row in enumerate(ordered, start=1):
        try:
            result.append(replace(row, nomor=nomor))
        except (TypeError, ValueError):
            result.append(row)
    return result


def bupot_sort_key(row) -> tuple:
    # Tanggal pemotongan paling representatif untuk kronologi Bupot.
    # Tanggal bukti menjadi fallback bila tanggal pemotongan kosong.
    date_year, date_month, date_day = _date_parts(
        getattr(row, "tanggal_pemotongan", "")
    )
    if not date_year:
        date_year, date_month, date_day = _date_parts(
            getattr(row, "tanggal_bukti", "")
        )

    fallback_year = _int(getattr(row, "tahun", 0))
    fallback_month = _month(getattr(row, "masa", ""))

    year = date_year or fallback_year
    month = date_month or fallback_month
    day = date_day or 0

    # Field tanggal/tahun yang tidak tersedia ditempatkan paling akhir.
    return (
        year if year > 0 else 9999,
        month if month > 0 else 99,
        day,
        str(getattr(row, "no_bupot", "") or "").strip().casefold(),
    )


def sort_bupot_rows(rows: Iterable) -> List:
    return sorted(list(rows or []), key=bupot_sort_key)
