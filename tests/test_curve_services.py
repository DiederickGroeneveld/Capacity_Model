from capacity_model.services.curve_data import build_probability_curve_dataframe
from capacity_model.services.factors import apply_scalar_factor, resolve_active_factor


def test_resolve_active_factor_multiplies_week_and_month() -> None:
    week_factor, month_factor, active_factor = resolve_active_factor(
        weekday_factors={"Monday": 1.1},
        month_factors={"Januari": 0.9},
        selected_weekday="Monday",
        selected_month="Januari",
    )

    assert week_factor == 1.1
    assert month_factor == 0.9
    assert active_factor == 0.99


def test_apply_scalar_factor_scales_all_values() -> None:
    scaled = apply_scalar_factor([1.0, 2.0, 3.0], 0.5)
    assert scaled == [0.5, 1.0, 1.5]


def test_build_probability_curve_dataframe_per_minute_has_1440_rows() -> None:
    curve_df, x_column = build_probability_curve_dataframe(
        means=[8.0, 12.0],
        std_devs=[1.0, 1.5],
        weights=[0.5, 0.5],
        per_minute=True,
        active_factor=1.0,
    )

    assert x_column == "Uur in dag"
    assert len(curve_df) == 24 * 60
    assert set(["Minuut in dag", "Uur in dag", "probability"]).issubset(curve_df.columns)
