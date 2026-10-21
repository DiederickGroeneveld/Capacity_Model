from datetime import date

from capacity_model.services.daily_probability_table import build_daily_probability_table


def test_build_daily_probability_table_shape_and_headers() -> None:
    result = build_daily_probability_table(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        means=[8.0, 12.0, 18.0],
        std_devs=[1.0, 1.5, 2.0],
        weights=[0.3, 0.4, 0.3],
        weekday_factors={
            "Monday": 1.1,
            "Tuesday": 1.1,
            "Wednesday": 1.1,
            "Thursday": 1.1,
            "Friday": 1.1,
            "Saturday": 0.8,
            "Sunday": 0.8,
        },
        month_factors={
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
        },
    )

    assert len(result) == 3
    assert result.columns[0:3].tolist() == ["Datum", "weekdag", "totaal"]
    assert result.columns[3] == "00:00"
    assert result.columns[-1] == "23:59"
    assert len(result.columns) == 3 + 1440
    assert result["totaal"].eq(1.0).all()

    minute_columns = result.columns[3:]
    minute_sums = result[minute_columns].sum(axis=1)
    assert minute_sums.round(12).eq(1.0).all()
