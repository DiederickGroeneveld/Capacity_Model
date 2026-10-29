from __future__ import annotations

import math

import numpy as np
import pandas as pd


def calculate_connection_capacity_kw(amperes: float, volt: float) -> float:
    """Calculate 3-phase connection capacity in kW.

    Formula: (sqrt(3) * A * V) / 1000
    """
    if amperes <= 0:
        raise ValueError("amperes must be > 0")
    if volt <= 0:
        raise ValueError("volt must be > 0")

    return (math.sqrt(3) * amperes * volt) / 1000


def build_cumulative_energy_flow_dataframe(
    loading_profile_df: pd.DataFrame,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    battery_size_kwh: float,
    connection_capacity_kw: float,
    session_draw_kwh_per_min: float = 1.16,
) -> pd.DataFrame:
    """Build minute-level cumulative energy flow from charging sessions.

    - Battery starts full on start_date 00:00.
    - Active sessions draw `session_draw_kwh_per_min` each minute.
    - Total draw per minute is capped by connection max capacity in kWh/min.
        - When there are no active sessions, battery recharges by connection max
            capacity in kWh/min (bounded by `battery_size_kwh`).
    """
    if battery_size_kwh <= 0:
        raise ValueError("battery_size_kwh must be > 0")
    if connection_capacity_kw <= 0:
        raise ValueError("connection_capacity_kw must be > 0")
    if session_draw_kwh_per_min <= 0:
        raise ValueError("session_draw_kwh_per_min must be > 0")

    start_ts = pd.Timestamp(start_date).normalize()
    end_ts = pd.Timestamp(end_date).normalize() + pd.Timedelta(hours=23, minutes=59)
    if end_ts < start_ts:
        raise ValueError("end_date must be on or after start_date")

    timeline = pd.date_range(start=start_ts, end=end_ts, freq="min")
    if len(timeline) == 0:
        return pd.DataFrame()

    active_delta = np.zeros(len(timeline) + 1, dtype=np.int32)
    served_sessions = loading_profile_df.copy()

    if "session_missed" in served_sessions.columns:
        served_sessions = served_sessions.loc[~served_sessions["session_missed"].astype(bool)]

    if not served_sessions.empty:
        served_sessions = served_sessions.copy()
        served_sessions["charging_start_datetime"] = pd.to_datetime(
            served_sessions.get("charging_start_datetime", served_sessions.get("arrival_datetime")),
            errors="coerce",
        )
        served_sessions["end_datetime"] = pd.to_datetime(served_sessions["end_datetime"], errors="coerce")
        served_sessions = served_sessions.dropna(subset=["charging_start_datetime", "end_datetime"])

        for _, session in served_sessions.iterrows():
            session_start = max(session["charging_start_datetime"], start_ts)
            session_end = min(session["end_datetime"], end_ts + pd.Timedelta(minutes=1))
            if session_end <= session_start:
                continue

            start_idx = int((session_start - start_ts).total_seconds() // 60)
            end_idx = int((session_end - start_ts).total_seconds() // 60)
            start_idx = max(0, min(start_idx, len(timeline)))
            end_idx = max(0, min(end_idx, len(timeline)))
            if end_idx > start_idx:
                active_delta[start_idx] += 1
                active_delta[end_idx] -= 1

    active_sessions = np.cumsum(active_delta[:-1])
    connection_cap_kwh_per_min = connection_capacity_kw / 60.0
    uncapped_draw_kwh_per_min = active_sessions * session_draw_kwh_per_min
    draw_kwh_per_min = np.minimum(uncapped_draw_kwh_per_min, connection_cap_kwh_per_min)

    cumulative_used_kwh = np.cumsum(draw_kwh_per_min)
    charge_kwh_per_min = np.where(active_sessions == 0, connection_cap_kwh_per_min, 0.0)

    battery_remaining_kwh = np.empty(len(timeline), dtype=float)
    current_battery_kwh = battery_size_kwh
    for idx in range(len(timeline)):
        current_battery_kwh -= draw_kwh_per_min[idx]
        current_battery_kwh = max(current_battery_kwh, 0.0)
        current_battery_kwh += charge_kwh_per_min[idx]
        current_battery_kwh = min(current_battery_kwh, battery_size_kwh)
        battery_remaining_kwh[idx] = current_battery_kwh

    return pd.DataFrame(
        {
            "timestamp": timeline,
            "active_sessions": active_sessions,
            "uncapped_draw_kwh_per_min": uncapped_draw_kwh_per_min,
            "draw_kwh_per_min": draw_kwh_per_min,
            "charge_kwh_per_min": charge_kwh_per_min,
            "cumulative_used_kwh": cumulative_used_kwh,
            "battery_remaining_kwh": battery_remaining_kwh,
            "connection_capacity_kw": connection_capacity_kw,
            "connection_capacity_kwh_per_min": connection_cap_kwh_per_min,
            "session_draw_kwh_per_min": session_draw_kwh_per_min,
            "battery_size_kwh": battery_size_kwh,
        }
    )
