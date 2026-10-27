import math

import pytest

from capacity_model.services.energy_flow import calculate_connection_capacity_kw


def test_calculate_connection_capacity_kw() -> None:
    capacity_kw = calculate_connection_capacity_kw(amperes=80, volt=400)
    expected = (math.sqrt(3) * 80 * 400) / 1000

    assert capacity_kw == pytest.approx(expected)


def test_calculate_connection_capacity_kw_invalid_values() -> None:
    with pytest.raises(ValueError):
        calculate_connection_capacity_kw(amperes=0, volt=400)

    with pytest.raises(ValueError):
        calculate_connection_capacity_kw(amperes=80, volt=0)
