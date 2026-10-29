import math

import pandas as pd
import pytest

from capacity_model.services.energy_flow import (
    apply_battery_constraints_to_loading_profile,
    build_cumulative_energy_flow_dataframe,
    calculate_connection_capacity_kw,
)


def test_calculate_connection_capacity_kw() -> None:
    capacity_kw = calculate_connection_capacity_kw(amperes=80, volt=400)
    expected = (math.sqrt(3) * 80 * 400) / 1000

    assert capacity_kw == pytest.approx(expected)


def test_calculate_connection_capacity_kw_invalid_values() -> None:
    with pytest.raises(ValueError):
        calculate_connection_capacity_kw(amperes=0, volt=400)

    with pytest.raises(ValueError):
        calculate_connection_capacity_kw(amperes=80, volt=0)


def test_build_cumulative_energy_flow_dataframe_subtracts_116_per_active_minute() -> None:
    loading_profile = pd.DataFrame(
        [
            {
                "session_id": 1,
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:03",
                "session_missed": False,
            }
        ]
    )

    result = build_cumulative_energy_flow_dataframe(
        loading_profile,
        start_date=pd.Timestamp("2026-01-01"),
        end_date=pd.Timestamp("2026-01-01"),
        battery_size_kwh=10.0,
        connection_capacity_kw=500.0,
        session_draw_kwh_per_min=1.16,
    )

    assert float(result.iloc[0]["battery_remaining_kwh"]) == pytest.approx(8.84)
    assert float(result.iloc[1]["battery_remaining_kwh"]) == pytest.approx(7.68)
    assert float(result.iloc[2]["battery_remaining_kwh"]) == pytest.approx(6.52)


def test_build_cumulative_energy_flow_dataframe_caps_draw_by_connection_capacity() -> None:
    loading_profile = pd.DataFrame(
        [
            {
                "session_id": 1,
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": False,
            },
            {
                "session_id": 2,
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": False,
            },
        ]
    )

    result = build_cumulative_energy_flow_dataframe(
        loading_profile,
        start_date=pd.Timestamp("2026-01-01"),
        end_date=pd.Timestamp("2026-01-01"),
        battery_size_kwh=20.0,
        connection_capacity_kw=60.0,
        session_draw_kwh_per_min=1.16,
    )

    assert float(result.iloc[0]["draw_kwh_per_min"]) == pytest.approx(1.0)
    assert float(result.iloc[1]["draw_kwh_per_min"]) == pytest.approx(1.0)


def test_build_cumulative_energy_flow_dataframe_recharges_when_idle() -> None:
    loading_profile = pd.DataFrame(
        [
            {
                "session_id": 1,
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": False,
            }
        ]
    )

    result = build_cumulative_energy_flow_dataframe(
        loading_profile,
        start_date=pd.Timestamp("2026-01-01"),
        end_date=pd.Timestamp("2026-01-01"),
        battery_size_kwh=3.0,
        connection_capacity_kw=60.0,
        session_draw_kwh_per_min=1.0,
    )

    assert float(result.iloc[0]["battery_remaining_kwh"]) == pytest.approx(2.0)
    assert float(result.iloc[1]["battery_remaining_kwh"]) == pytest.approx(1.0)
    assert float(result.iloc[2]["battery_remaining_kwh"]) == pytest.approx(2.0)
    assert float(result.iloc[3]["battery_remaining_kwh"]) == pytest.approx(3.0)
    assert float(result.iloc[2]["charge_kwh_per_min"]) == pytest.approx(1.0)


def test_build_cumulative_energy_flow_dataframe_recharge_is_capped_at_battery_size() -> None:
    result = build_cumulative_energy_flow_dataframe(
        pd.DataFrame(),
        start_date=pd.Timestamp("2026-01-01"),
        end_date=pd.Timestamp("2026-01-01"),
        battery_size_kwh=5.0,
        connection_capacity_kw=120.0,
        session_draw_kwh_per_min=1.16,
    )

    assert float(result.iloc[0]["battery_remaining_kwh"]) == pytest.approx(5.0)
    assert float(result.iloc[10]["battery_remaining_kwh"]) == pytest.approx(5.0)


def test_apply_battery_constraints_marks_sessions_missed_when_battery_is_empty() -> None:
    loading_profile = pd.DataFrame(
        [
            {
                "session_id": 1,
                "arrival_datetime": "2026-01-01 00:00",
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": False,
                "used_pistol": "pistol_1",
            },
            {
                "session_id": 2,
                "arrival_datetime": "2026-01-01 00:00",
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": False,
                "used_pistol": "pistol_2",
            },
        ]
    )

    result = apply_battery_constraints_to_loading_profile(
        loading_profile,
        battery_size_kwh=1.0,
        connection_capacity_kw=60.0,
        session_draw_kwh_per_min=1.0,
    )

    assert result["session_missed_by_battery"].all()
    assert result["session_missed"].all()
    assert result["missed_reason"].eq("battery_empty").all()
    assert result["used_pistol"].eq("missed_battery").all()
    assert result["missed_sessions_at_arrival_time"].eq(2).all()


def test_apply_battery_constraints_preserves_existing_pistol_misses() -> None:
    loading_profile = pd.DataFrame(
        [
            {
                "session_id": 1,
                "arrival_datetime": "2026-01-01 00:00",
                "charging_start_datetime": "2026-01-01 00:00",
                "end_datetime": "2026-01-01 00:02",
                "session_missed": True,
                "used_pistol": "missed",
            }
        ]
    )

    result = apply_battery_constraints_to_loading_profile(
        loading_profile,
        battery_size_kwh=1.0,
        connection_capacity_kw=60.0,
        session_draw_kwh_per_min=1.0,
    )

    assert bool(result.iloc[0]["session_missed"]) is True
    assert bool(result.iloc[0]["session_missed_by_battery"]) is False
    assert str(result.iloc[0]["missed_reason"]) == "pistol_unavailable"
