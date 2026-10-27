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
    recapture_rate: float = 0.2,
    in_progress_threshold_min: float = 10.0,
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
    if not 0 <= recapture_rate <= 1:
        raise ValueError("recapture_rate must be between 0 and 1")
    if in_progress_threshold_min < 0:
        raise ValueError("in_progress_threshold_min must be >= 0")

    minute_columns = _minute_columns(simulated_arrivals_df)
    if not minute_columns:
        raise ValueError("No minute columns found. Expected columns like '00:00' ... '23:59'.")

    rng = np.random.default_rng(random_seed)
    connector_count = number_of_charge_points * 2

    baseline_kwh = average_duration_min * charge_speed_kwh_per_min
    kwh_scale = average_kwh / baseline_kwh if baseline_kwh > 0 else 1.0

    records: list[dict[str, int | float | str | bool]] = []
    session_id = 0
    pistol_available_at: list[datetime] = [datetime.min for _ in range(connector_count)]

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
                charging_start_datetime = arrival_datetime

                assigned_pistol_index: int | None = None
                for index, available_at in enumerate(pistol_available_at):
                    if available_at <= arrival_datetime:
                        assigned_pistol_index = index
                        break

                missed_at_arrival = assigned_pistol_index is None

                minutes_until_next_available: float | None = None
                session_in_progress_within_threshold = False
                recaptured_session = False

                if missed_at_arrival:
                    earliest_available = min(pistol_available_at)
                    minutes_until_next_available = max(
                        0.0,
                        (earliest_available - arrival_datetime).total_seconds() / 60.0,
                    )
                    session_in_progress_within_threshold = (
                        minutes_until_next_available <= in_progress_threshold_min
                    )

                    if session_in_progress_within_threshold and rng.random() < recapture_rate:
                        assigned_pistol_index = int(np.argmin(pistol_available_at))
                        charging_start_datetime = pistol_available_at[assigned_pistol_index]
                        recaptured_session = True

                if assigned_pistol_index is not None:
                    end_datetime = charging_start_datetime + timedelta(minutes=duration_min)
                    pistol_available_at[assigned_pistol_index] = end_datetime
                else:
                    end_datetime = arrival_datetime + timedelta(minutes=duration_min)

                session_missed = assigned_pistol_index is None
                used_pistol = f"pistol_{assigned_pistol_index + 1}" if assigned_pistol_index is not None else "missed"

                pistol_usage_columns = {
                    f"pistol_{index + 1}_in_use": int(assigned_pistol_index == index)
                    for index in range(connector_count)
                }

                records.append(
                    {
                        "session_id": session_id,
                        "Datum": date_text,
                        "weekdag": weekday_text,
                        "arrival_minute": minute_label,
                        "arrival_datetime": arrival_datetime.strftime("%Y-%m-%d %H:%M"),
                        "charging_start_datetime": charging_start_datetime.strftime("%Y-%m-%d %H:%M"),
                        "duration_min": duration_min,
                        "end_datetime": end_datetime.strftime("%Y-%m-%d %H:%M"),
                        "energy_kwh": round(float(energy_kwh), 3),
                        "aantal_laadpunten": number_of_charge_points,
                        "aantal_pistolen": connector_count,
                        "used_pistol": used_pistol,
                        "missed_at_arrival": missed_at_arrival,
                        "minutes_until_next_available": (
                            round(float(minutes_until_next_available), 3)
                            if minutes_until_next_available is not None
                            else np.nan
                        ),
                        "session_in_progress_within_threshold": session_in_progress_within_threshold,
                        "recaptured_session": recaptured_session,
                        "session_missed": session_missed,
                        "recapture_rate": recapture_rate,
                        "in_progress_threshold_min": in_progress_threshold_min,
                        **pistol_usage_columns,
                    }
                )

    profile_df = pd.DataFrame(records)
    if profile_df.empty:
        return profile_df

    missed_counts = (
        profile_df.loc[profile_df["session_missed"]]
        .groupby("arrival_datetime")
        .size()
        .to_dict()
    )
    profile_df["missed_sessions_at_arrival_time"] = profile_df["arrival_datetime"].map(missed_counts).fillna(0).astype(int)

    return profile_df
