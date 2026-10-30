from datetime import date

from capacity_model.services.daily_probability_table import build_daily_probability_table
from capacity_model.services.sensitivity import build_sensitivity_analysis_dataframe


def _weekday_factors() -> dict[str, float]:
    return {
        "Monday": 1.1,
        "Tuesday": 1.1,
        "Wednesday": 1.1,
        "Thursday": 1.1,
        "Friday": 1.1,
        "Saturday": 0.8,
        "Sunday": 0.8,
    }


def _month_factors() -> dict[str, float]:
    return {
        "Januari": 1.0,
        "Februari": 1.0,
        "Maart": 1.0,
        "April": 1.0,
        "Mei": 1.0,
        "Juni": 1.0,
        "Juli": 1.0,
        "Augustus": 1.0,
        "September": 1.0,
        "Oktober": 1.0,
        "November": 1.0,
        "December": 1.0,
    }


def test_build_sensitivity_analysis_dataframe_includes_requested_scenarios() -> None:
    probability_table = build_daily_probability_table(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        means=[8.0, 12.0, 18.0],
        std_devs=[1.0, 1.5, 2.0],
        weights=[0.3, 0.4, 0.3],
        weekday_factors=_weekday_factors(),
        month_factors=_month_factors(),
    )

    result = build_sensitivity_analysis_dataframe(
        probability_table,
        trials=100,
        number_of_charge_points_options=[1, 2],
        expected_sessions_options=[0, 1, 2],
        average_duration_min=35.0,
        duration_spread_min=10.0,
        charge_speed_kwh_per_min=1.16,
        average_kwh=40.6,
        recapture_rate=0.2,
        in_progress_threshold_min=10.0,
        battery_size_kwh=260.0,
        connection_capacity_kw=55.0,
        market_price_kwh_ex_btw=0.19,
        retail_price_kwh_ex_btw=0.59,
        random_seed=42,
    )

    assert len(result) == 6
    assert {
        "expected_sessions_per_day",
        "number_of_charge_points",
        "total_turnover_ex_btw",
        "total_profit_ex_btw",
        "total_charge_sessions",
        "missed_sessions_spots",
        "missed_sessions_battery",
    }.issubset(result.columns)

    zero_sessions_rows = result.loc[result["expected_sessions_per_day"] == 0]
    assert zero_sessions_rows["total_turnover_ex_btw"].eq(0.0).all()
    assert zero_sessions_rows["total_profit_ex_btw"].eq(0.0).all()
    assert zero_sessions_rows["total_charge_sessions"].eq(0).all()
    assert zero_sessions_rows["missed_sessions_spots"].eq(0).all()
    assert zero_sessions_rows["missed_sessions_battery"].eq(0).all()
