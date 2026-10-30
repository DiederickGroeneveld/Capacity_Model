from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from capacity_model.services.arrival_simulation import simulate_daily_arrivals_from_probability_table
from capacity_model.services.energy_flow import apply_battery_constraints_to_loading_profile
from capacity_model.services.loading_profile import simulate_loading_profile_from_arrivals
from capacity_model.services.session_finance import add_session_financials, build_financial_kpis


def _minute_columns(dataframe: pd.DataFrame) -> list[str]:
    return [column for column in dataframe.columns if ":" in str(column)]


def _simulate_arrivals_allow_zero(
    probability_table_df: pd.DataFrame,
    *,
    expected_sessions: int,
    trials: int,
    random_seed: int,
) -> pd.DataFrame:
    if expected_sessions == 0:
        minute_columns = _minute_columns(probability_table_df)
        zero_arrivals_df = probability_table_df[["Datum", "weekdag"]].copy()
        zero_arrivals_df["expected_sessions"] = 0
        zero_arrivals_df["trials"] = trials
        zero_arrivals_df["totaal_simulated"] = 0
        for column in minute_columns:
            zero_arrivals_df[column] = 0
        return zero_arrivals_df

    return simulate_daily_arrivals_from_probability_table(
        probability_table_df,
        expected_sessions=expected_sessions,
        trials=trials,
        random_seed=random_seed,
    )


def _get_missed_sessions_by_reason(loading_profile_df: pd.DataFrame) -> tuple[int, int]:
    if loading_profile_df.empty:
        return 0, 0

    if "missed_reason" in loading_profile_df.columns:
        reasons = loading_profile_df["missed_reason"].astype(str)
        missed_pistol = int((reasons == "pistol_unavailable").sum())
        missed_battery = int((reasons == "battery_empty").sum())
        return missed_pistol, missed_battery

    if "session_missed_by_battery" in loading_profile_df.columns and "session_missed" in loading_profile_df.columns:
        missed_battery = int(loading_profile_df["session_missed_by_battery"].astype(bool).sum())
        missed_total = int(loading_profile_df["session_missed"].astype(bool).sum())
        missed_pistol = max(0, missed_total - missed_battery)
        return missed_pistol, missed_battery

    if "session_missed" in loading_profile_df.columns:
        return int(loading_profile_df["session_missed"].astype(bool).sum()), 0

    return 0, 0


def build_sensitivity_analysis_dataframe(
    probability_table_df: pd.DataFrame,
    *,
    trials: int,
    number_of_charge_points_options: Sequence[int],
    expected_sessions_options: Sequence[int],
    average_duration_min: float,
    duration_spread_min: float,
    charge_speed_kwh_per_min: float,
    average_kwh: float,
    recapture_rate: float,
    in_progress_threshold_min: float,
    battery_size_kwh: float,
    connection_capacity_kw: float,
    market_price_kwh_ex_btw: float,
    retail_price_kwh_ex_btw: float,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Run sensitivity analysis over session/day and charge-point scenarios."""
    rows: list[dict[str, int | float]] = []

    for number_of_charge_points in number_of_charge_points_options:
        for expected_sessions in expected_sessions_options:
            simulated_arrivals_df = _simulate_arrivals_allow_zero(
                probability_table_df,
                expected_sessions=expected_sessions,
                trials=trials,
                random_seed=random_seed,
            )

            loading_profile_df = simulate_loading_profile_from_arrivals(
                simulated_arrivals_df,
                number_of_charge_points=number_of_charge_points,
                average_duration_min=average_duration_min,
                duration_spread_min=duration_spread_min,
                charge_speed_kwh_per_min=charge_speed_kwh_per_min,
                average_kwh=average_kwh,
                recapture_rate=recapture_rate,
                in_progress_threshold_min=in_progress_threshold_min,
                random_seed=random_seed,
            )
            loading_profile_df = apply_battery_constraints_to_loading_profile(
                loading_profile_df,
                battery_size_kwh=battery_size_kwh,
                connection_capacity_kw=connection_capacity_kw,
                session_draw_kwh_per_min=charge_speed_kwh_per_min,
            )
            loading_profile_df = add_session_financials(
                loading_profile_df,
                market_price_kwh_ex_btw=market_price_kwh_ex_btw,
                retail_price_kwh_ex_btw=retail_price_kwh_ex_btw,
            )

            kpis = build_financial_kpis(
                loading_profile_df,
                market_price_kwh_ex_btw=market_price_kwh_ex_btw,
                retail_price_kwh_ex_btw=retail_price_kwh_ex_btw,
            )

            missed_pistol, missed_battery = _get_missed_sessions_by_reason(loading_profile_df)

            if loading_profile_df.empty:
                total_charge_sessions = 0
            elif "session_missed" in loading_profile_df.columns:
                total_charge_sessions = int((~loading_profile_df["session_missed"].astype(bool)).sum())
            else:
                total_charge_sessions = int(len(loading_profile_df))

            rows.append(
                {
                    "expected_sessions_per_day": int(expected_sessions),
                    "number_of_charge_points": int(number_of_charge_points),
                    "total_turnover_ex_btw": float(kpis["total_turnover_ex_btw"]),
                    "total_profit_ex_btw": float(kpis["total_profit_ex_btw"]),
                    "total_charge_sessions": int(total_charge_sessions),
                    "missed_sessions_spots": int(missed_pistol),
                    "missed_sessions_battery": int(missed_battery),
                }
            )

    return pd.DataFrame(rows)
