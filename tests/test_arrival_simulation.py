from datetime import date

from capacity_model.services.arrival_simulation import (
    simulate_daily_arrivals,
    simulate_daily_arrivals_from_probability_table,
)
from capacity_model.services.daily_probability_table import build_daily_probability_table


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


def test_simulate_daily_arrivals_from_probability_table_shape_and_types() -> None:
    probability_table = build_daily_probability_table(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        means=[8.0, 12.0, 18.0],
        std_devs=[1.0, 1.5, 2.0],
        weights=[0.3, 0.4, 0.3],
        weekday_factors=_weekday_factors(),
        month_factors=_month_factors(),
    )

    simulated = simulate_daily_arrivals_from_probability_table(
        probability_table,
        expected_sessions=50,
        trials=1000,
        random_seed=7,
    )

    assert len(simulated) == 2
    assert simulated.columns[0:4].tolist() == [
        "Datum",
        "weekdag",
        "expected_sessions",
        "trials",
    ]
    assert simulated.columns[4] == "totaal_simulated"
    assert simulated.columns[5] == "00:00"
    assert simulated.columns[-1] == "23:59"

    minute_columns = [column for column in simulated.columns if ":" in column]
    assert simulated[minute_columns].ge(0).all().all()
    assert simulated[minute_columns].dtypes.apply(lambda dtype: dtype.kind in {"i", "u"}).all()


def test_simulation_is_reproducible_for_fixed_seed() -> None:
    result_1 = simulate_daily_arrivals(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        means=[8.0, 12.0, 18.0],
        std_devs=[1.0, 1.5, 2.0],
        weights=[0.3, 0.4, 0.3],
        weekday_factors=_weekday_factors(),
        month_factors=_month_factors(),
        expected_sessions=50,
        trials=1000,
        random_seed=42,
    )

    result_2 = simulate_daily_arrivals(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        means=[8.0, 12.0, 18.0],
        std_devs=[1.0, 1.5, 2.0],
        weights=[0.3, 0.4, 0.3],
        weekday_factors=_weekday_factors(),
        month_factors=_month_factors(),
        expected_sessions=50,
        trials=1000,
        random_seed=42,
    )

    assert result_1.equals(result_2)
