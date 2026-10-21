from __future__ import annotations

from datetime import date
import re
from typing import Sequence

import numpy as np
import pandas as pd

from capacity_model.services.daily_probability_table import build_daily_probability_table

_MINUTE_COLUMN_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def _minute_columns(dataframe: pd.DataFrame) -> list[str]:
    return [column for column in dataframe.columns if _MINUTE_COLUMN_PATTERN.match(str(column))]


def simulate_daily_arrivals_from_probability_table(
    probability_table: pd.DataFrame,
    *,
    expected_sessions: int,
    trials: int = 1000,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Simulate minute-level arrivals per day from a daily probability table.

    Expected input columns:
    - `Datum`
    - `weekdag`
    - minute columns from `00:00` to `23:59`

    Per minute simulation uses expected sessions as expected successes and a
    separate number of trials:

    1. Build minute weights from the day profile.
    2. Expected minute successes = expected_sessions * minute_weight.
    3. Sample: Binomial(n=trials, p=min(1, expected_minute_successes / trials)).
    """
    minute_columns = _minute_columns(probability_table)
    if not minute_columns:
        raise ValueError("No minute columns found. Expected columns like '00:00' ... '23:59'.")

    if expected_sessions <= 0:
        raise ValueError("expected_sessions must be > 0")

    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = np.random.default_rng(random_seed)
    simulated_rows: list[dict[str, float | int | str]] = []

    for _, row in probability_table.iterrows():
        profile_values = np.array([float(row[column]) for column in minute_columns], dtype=float)
        if (profile_values < 0).any():
            raise ValueError("Minute expected values must be >= 0 for simulation.")

        profile_sum = float(profile_values.sum())
        if profile_sum > 0:
            minute_weights = profile_values / profile_sum
        else:
            minute_weights = np.zeros(len(minute_columns), dtype=float)

        expected_successes_per_minute = expected_sessions * minute_weights

        p_values = np.minimum(1.0, expected_successes_per_minute / float(trials))
        minute_counts = rng.binomial(trials, p_values)


        simulated_row: dict[str, float | int | str] = {
            "Datum": str(row.get("Datum", "")),
            "weekdag": str(row.get("weekdag", "")),
            "expected_sessions": expected_sessions,
            "trials": trials,
            "totaal_simulated": int(minute_counts.sum()),
        }
        simulated_row.update({column: int(value) for column, value in zip(minute_columns, minute_counts)})
        simulated_rows.append(simulated_row)

    return pd.DataFrame(simulated_rows)


def simulate_daily_arrivals(
    *,
    start_date: date,
    end_date: date,
    means: Sequence[float],
    std_devs: Sequence[float],
    weights: Sequence[float] | None,
    weekday_factors: dict[str, float],
    month_factors: dict[str, float],
    expected_sessions: int,
    trials: int = 1000,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Build probability table and simulate daily minute-level arrivals."""
    probability_table = build_daily_probability_table(
        start_date=start_date,
        end_date=end_date,
        means=means,
        std_devs=std_devs,
        weights=weights,
        weekday_factors=weekday_factors,
        month_factors=month_factors,
    )

    return simulate_daily_arrivals_from_probability_table(
        probability_table,
        expected_sessions=expected_sessions,
        trials=trials,
        random_seed=random_seed,
    )
