from __future__ import annotations

from datetime import datetime, timedelta
import re

import numpy as np
import pandas as pd

_MINUTE_COLUMN_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def _minute_columns(dataframe: pd.DataFrame) -> list[str]:
    return [column for column in dataframe.columns if _MINUTE_COLUMN_PATTERN.match(str(column))]


def _sample_duration_minutes(
    rng: np.random.Generator,
    average_duration_min: float,
    duration_spread_min: float,
) -> int:
    poisson_sample = float(rng.poisson(lam=max(average_duration_min, 1e-9)))

    if duration_spread_min <= 0:
        return max(1, int(round(average_duration_min)))

    poisson_std = np.sqrt(max(average_duration_min, 1e-9))
    spread_scale = duration_spread_min / poisson_std
    adjusted = average_duration_min + (poisson_sample - average_duration_min) * spread_scale
    return max(1, int(round(adjusted)))


def simulate_loading_profile_from_arrivals(
    simulated_arrivals_df: pd.DataFrame,
    *,
    number_of_charge_points: int,
    average_duration_min: float,
    duration_spread_min: float,
    charge_speed_kwh_per_min: float,
    average_kwh: float,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Simulate loading time per arrival based on minute-level arrivals.

    Input expected columns in `simulated_arrivals_df`:
    - `Datum` in `%d/%m/%Y`
    - `weekdag`
    - minute columns from `00:00` to `23:59` with integer arrival counts
    """
    if number_of_charge_points <= 0:
        raise ValueError("number_of_charge_points must be > 0")
    if average_duration_min <= 0:
        raise ValueError("average_duration_min must be > 0")
    if charge_speed_kwh_per_min <= 0:
        raise ValueError("charge_speed_kwh_per_min must be > 0")
    if average_kwh <= 0:
        raise ValueError("average_kwh must be > 0")

    minute_columns = _minute_columns(simulated_arrivals_df)
    if not minute_columns:
        raise ValueError("No minute columns found. Expected columns like '00:00' ... '23:59'.")

    rng = np.random.default_rng(random_seed)
    connector_count = number_of_charge_points * 2

    baseline_kwh = average_duration_min * charge_speed_kwh_per_min
    kwh_scale = average_kwh / baseline_kwh if baseline_kwh > 0 else 1.0

    records: list[dict[str, int | float | str]] = []
    session_id = 0

    for _, row in simulated_arrivals_df.iterrows():
        date_text = str(row.get("Datum", ""))
        weekday_text = str(row.get("weekdag", ""))
        day_date = datetime.strptime(date_text, "%d/%m/%Y").date()

        for minute_label in minute_columns:
            arrivals = int(row[minute_label])
            if arrivals <= 0:
                continue

            hour, minute = [int(part) for part in minute_label.split(":")]
            arrival_datetime = datetime.combine(day_date, datetime.min.time()).replace(hour=hour, minute=minute)

            for _ in range(arrivals):
                session_id += 1
                duration_min = _sample_duration_minutes(rng, average_duration_min, duration_spread_min)
                energy_kwh = duration_min * charge_speed_kwh_per_min * kwh_scale

                records.append(
                    {
                        "session_id": session_id,
                        "Datum": date_text,
                        "weekdag": weekday_text,
                        "arrival_minute": minute_label,
                        "arrival_datetime": arrival_datetime.strftime("%Y-%m-%d %H:%M"),
                        "duration_min": duration_min,
                        "end_datetime": (arrival_datetime + timedelta(minutes=duration_min)).strftime("%Y-%m-%d %H:%M"),
                        "energy_kwh": round(float(energy_kwh), 3),
                        "aantal_laadpunten": number_of_charge_points,
                        "aantal_pistolen": connector_count,
                    }
                )

    return pd.DataFrame(records)
