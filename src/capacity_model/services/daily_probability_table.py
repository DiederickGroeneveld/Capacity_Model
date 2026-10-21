from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

import pandas as pd

from capacity_model.data import MONTH_DEFAULT_FACTORS, WEEKDAY_DEFAULT_FACTORS
from capacity_model.services.distributions import combine_normal_distributions

WEEKDAY_NAMES = list(WEEKDAY_DEFAULT_FACTORS.keys())
MONTH_NAMES = list(MONTH_DEFAULT_FACTORS.keys())


def _minute_headers() -> list[str]:
    return [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in range(60)]


def build_daily_probability_table(
    start_date: date,
    end_date: date,
    means: Sequence[float],
    std_devs: Sequence[float],
    weights: Sequence[float] | None,
    weekday_factors: dict[str, float],
    month_factors: dict[str, float],
) -> pd.DataFrame:
    """Build a wide table with one row per day and one column per minute of day.

    Columns:
    - Datum (dd/mm/YYYY)
    - weekdag
    - totaal
    - 00:00 .. 23:59
    """
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    minute_headers = _minute_headers()
    x_values = [minute / 60.0 for minute in range(24 * 60)]
    _, base_probabilities = combine_normal_distributions(
        means=means,
        std_devs=std_devs,
        weights=weights,
        x_values=x_values,
    )

    records: list[dict[str, float | str]] = []
    current_date = start_date

    while current_date <= end_date:
        weekday_name = WEEKDAY_NAMES[current_date.weekday()]
        month_name = MONTH_NAMES[current_date.month - 1]

        week_factor = float(weekday_factors.get(weekday_name, 1.0))
        month_factor = float(month_factors.get(month_name, 1.0))
        active_factor = week_factor * month_factor

        minute_values = [value * active_factor for value in base_probabilities]
        total_value = float(sum(minute_values))

        if total_value > 0:
            minute_probabilities = [value / total_value for value in minute_values]
        else:
            minute_probabilities = [0.0 for _ in minute_values]

        row: dict[str, float | str] = {
            "Datum": current_date.strftime("%d/%m/%Y"),
            "weekdag": weekday_name,
            "totaal": total_value,
        }
        row.update({header: value for header, value in zip(minute_headers, minute_probabilities)})
        records.append(row)

        current_date += timedelta(days=1)

    columns = ["Datum", "weekdag", "totaal", *minute_headers]
    return pd.DataFrame(records, columns=columns)
