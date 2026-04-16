from __future__ import annotations

from datetime import date
from typing import Iterable

BASHO_MONTHS = (1, 3, 5, 7, 9, 11)


def basho_id(year: int, month: int) -> str:
    if month not in BASHO_MONTHS:
        raise ValueError(f"{month} is not a standard honbasho month")
    return f"{year}{month:02d}"


def split_basho_id(value: str) -> tuple[int, int]:
    if len(value) != 6 or not value.isdigit():
        raise ValueError(f"Invalid basho id: {value!r}")
    year = int(value[:4])
    month = int(value[4:])
    if month not in BASHO_MONTHS:
        raise ValueError(f"Invalid basho month in {value!r}")
    return year, month


def iter_basho_ids(
    start_year: int,
    end_year: int,
    *,
    as_of: date | None = None,
    include_future: bool = False,
) -> Iterable[str]:
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year")
    as_of = as_of or date.today()
    for year in range(start_year, end_year + 1):
        for month in BASHO_MONTHS:
            if not include_future and (year, month) > (as_of.year, as_of.month):
                continue
            yield basho_id(year, month)
