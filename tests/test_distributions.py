import pytest

from Calculations.Functions import combine_normal_distributions


def test_combine_normal_distributions_returns_curve_with_expected_length() -> None:
    x, y = combine_normal_distributions(
        means=[0.0, 3.0],
        std_devs=[1.0, 1.5],
        weights=[0.6, 0.4],
        num_points=300,
    )

    assert len(x) == 300
    assert len(y) == 300
    assert all(value >= 0 for value in y)


def test_combine_normal_distributions_curve_area_is_close_to_one() -> None:
    x, y = combine_normal_distributions(
        means=[0.0, 5.0],
        std_devs=[1.0, 2.0],
        weights=[0.7, 0.3],
        num_points=1000,
    )

    area = 0.0
    for i in range(len(x) - 1):
        width = x[i + 1] - x[i]
        area += 0.5 * (y[i] + y[i + 1]) * width

    assert area == pytest.approx(1.0, rel=1e-12, abs=1e-12)


def test_combine_normal_distributions_respects_weights() -> None:
    x_values = [0.0]

    _, y_left = combine_normal_distributions(
        means=[0.0, 10.0],
        std_devs=[1.0, 1.0],
        weights=[1.0, 0.0],
        x_values=x_values,
    )

    _, y_right = combine_normal_distributions(
        means=[0.0, 10.0],
        std_devs=[1.0, 1.0],
        weights=[0.0, 1.0],
        x_values=x_values,
    )

    assert y_left[0] > y_right[0]
