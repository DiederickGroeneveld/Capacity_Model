import pandas as pd

from capacity_model.services.capacity import build_kpis, summarize_capacity


def test_summarize_capacity_adds_expected_columns() -> None:
    dataframe = pd.DataFrame(
        [
            {"team": "Ops", "period": "2026-Q1", "capacity": 100, "demand": 75},
            {"team": "Ops", "period": "2026-Q2", "capacity": 80, "demand": 90},
        ]
    )

    summary = summarize_capacity(dataframe)

    assert summary["gap"].tolist() == [25, -10]
    assert summary["status"].tolist() == ["Surplus", "Shortfall"]


def test_build_kpis_returns_totals() -> None:
    dataframe = pd.DataFrame(
        [
            {"capacity": 100, "demand": 75, "gap": 25},
            {"capacity": 80, "demand": 90, "gap": -10},
        ]
    )

    kpis = build_kpis(dataframe)

    assert kpis == {
        "total_capacity": 180.0,
        "total_demand": 165.0,
        "total_gap": 15.0,
        "utilization_pct": 91.7,
    }
