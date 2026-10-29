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


def apply_battery_constraints_to_loading_profile(
    loading_profile_df: pd.DataFrame,
    *,
    battery_size_kwh: float,
    connection_capacity_kw: float,
    session_draw_kwh_per_min: float = 1.16,
) -> pd.DataFrame:
    """Mark sessions as missed when battery becomes empty while they are charging.

    Existing missed sessions (e.g. no available pistol) are preserved.
    """
    if battery_size_kwh <= 0:
        raise ValueError("battery_size_kwh must be > 0")
    if connection_capacity_kw <= 0:
        raise ValueError("connection_capacity_kw must be > 0")
    if session_draw_kwh_per_min <= 0:
        raise ValueError("session_draw_kwh_per_min must be > 0")

    result = loading_profile_df.copy()
    if result.empty:
        result["session_missed_by_battery"] = pd.Series(dtype=bool)
        result["missed_reason"] = pd.Series(dtype=str)
        return result

    if "session_missed" not in result.columns:
        result["session_missed"] = False

    pre_missed_mask = result["session_missed"].astype(bool)
    result["session_missed_by_battery"] = False

    candidate = result.loc[~pre_missed_mask].copy()
    if candidate.empty:
        result["missed_reason"] = np.where(pre_missed_mask, "pistol_unavailable", "")
        return result

    candidate["charging_start_datetime"] = pd.to_datetime(
        candidate.get("charging_start_datetime", candidate.get("arrival_datetime")),
        errors="coerce",
    )
    candidate["end_datetime"] = pd.to_datetime(candidate["end_datetime"], errors="coerce")
    candidate = candidate.dropna(subset=["charging_start_datetime", "end_datetime"])
    candidate = candidate.loc[candidate["end_datetime"] > candidate["charging_start_datetime"]]

    if candidate.empty:
        result["missed_reason"] = np.where(pre_missed_mask, "pistol_unavailable", "")
        return result

    start_ts = candidate["charging_start_datetime"].min().floor("min")
    end_ts = candidate["end_datetime"].max().ceil("min")
    timeline = pd.date_range(start=start_ts, end=end_ts - pd.Timedelta(minutes=1), freq="min")
    if len(timeline) == 0:
        result["missed_reason"] = np.where(pre_missed_mask, "pistol_unavailable", "")
        return result

    total_minutes = len(timeline)
    starts_by_idx: dict[int, list[int]] = {}
    ends_by_idx: dict[int, list[int]] = {}

    for row_index, session in candidate.iterrows():
        session_start = session["charging_start_datetime"]
        session_end = session["end_datetime"]

        start_idx = int((session_start - start_ts).total_seconds() // 60)
        end_idx = int((session_end - start_ts).total_seconds() // 60)
        start_idx = max(0, min(start_idx, total_minutes))
        end_idx = max(0, min(end_idx, total_minutes))
        if end_idx <= start_idx:
            continue

        starts_by_idx.setdefault(start_idx, []).append(int(row_index))
        ends_by_idx.setdefault(end_idx, []).append(int(row_index))

    battery_missed_indices: set[int] = set()
    active_indices: set[int] = set()
    connection_cap_kwh_per_min = connection_capacity_kw / 60.0
    current_battery_kwh = float(battery_size_kwh)

    for idx in range(total_minutes):
        for session_index in ends_by_idx.get(idx, []):
            active_indices.discard(session_index)
        for session_index in starts_by_idx.get(idx, []):
            active_indices.add(session_index)

        active_count = len(active_indices)
        if active_count > 0:
            requested_draw = min(active_count * session_draw_kwh_per_min, connection_cap_kwh_per_min)
            actual_draw = min(requested_draw, current_battery_kwh)
            shortage = requested_draw - actual_draw
            if shortage > 1e-9:
                battery_missed_indices.update(active_indices)
            current_battery_kwh = max(current_battery_kwh - actual_draw, 0.0)
        else:
            current_battery_kwh = min(current_battery_kwh + connection_cap_kwh_per_min, battery_size_kwh)

    if battery_missed_indices:
        missed_index = result.index.intersection(list(battery_missed_indices))
        result.loc[missed_index, "session_missed_by_battery"] = True

    result["session_missed"] = result["session_missed"].astype(bool) | result["session_missed_by_battery"].astype(bool)

    if "used_pistol" in result.columns:
        battery_only_mask = result["session_missed_by_battery"].astype(bool) & ~pre_missed_mask
        result.loc[battery_only_mask, "used_pistol"] = "missed_battery"

    result["missed_reason"] = ""
    result.loc[pre_missed_mask, "missed_reason"] = "pistol_unavailable"
    result.loc[result["session_missed_by_battery"].astype(bool), "missed_reason"] = "battery_empty"

    if "arrival_datetime" in result.columns:
        missed_counts = (
            result.loc[result["session_missed"].astype(bool)]
            .groupby("arrival_datetime")
            .size()
            .to_dict()
        )
        result["missed_sessions_at_arrival_time"] = (
            result["arrival_datetime"].map(missed_counts).fillna(0).astype(int)
        )

    return result


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
