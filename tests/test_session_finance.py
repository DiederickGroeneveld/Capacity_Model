import pandas as pd
import pytest

from capacity_model.services.session_finance import add_session_financials, build_financial_kpis


def test_add_session_financials_adds_per_session_turnover_and_profit() -> None:
    loading_profile_df = pd.DataFrame(
        [
            {"session_id": 1, "energy_kwh": 10.0, "session_missed": False},
            {"session_id": 2, "energy_kwh": 5.0, "session_missed": True},
            {"session_id": 3, "energy_kwh": 4.0, "session_missed": False},
        ]
    )

    result = add_session_financials(
        loading_profile_df,
        market_price_kwh_ex_btw=0.19,
        retail_price_kwh_ex_btw=0.59,
    )

    assert result["billable_energy_kwh"].tolist() == pytest.approx([10.0, 0.0, 4.0])
    assert result["session_turnover_ex_btw"].tolist() == pytest.approx([5.9, 0.0, 2.36])
    assert result["session_market_cost_ex_btw"].tolist() == pytest.approx([1.9, 0.0, 0.76])
    assert result["session_profit_ex_btw"].tolist() == pytest.approx([4.0, 0.0, 1.6])


def test_build_financial_kpis_returns_totals() -> None:
    loading_profile_df = pd.DataFrame(
        [
            {"session_id": 1, "energy_kwh": 10.0, "session_missed": False},
            {"session_id": 2, "energy_kwh": 5.0, "session_missed": True},
            {"session_id": 3, "energy_kwh": 4.0, "session_missed": False},
        ]
    )

    kpis = build_financial_kpis(
        loading_profile_df,
        market_price_kwh_ex_btw=0.19,
        retail_price_kwh_ex_btw=0.59,
    )

    assert kpis == {
        "total_turnover_ex_btw": pytest.approx(8.26),
        "total_market_cost_ex_btw": pytest.approx(2.66),
        "total_profit_ex_btw": pytest.approx(5.6),
    }


def test_add_session_financials_rejects_negative_prices() -> None:
    loading_profile_df = pd.DataFrame([{"energy_kwh": 1.0}])

    with pytest.raises(ValueError):
        add_session_financials(
            loading_profile_df,
            market_price_kwh_ex_btw=-0.01,
            retail_price_kwh_ex_btw=0.59,
        )

    with pytest.raises(ValueError):
        add_session_financials(
            loading_profile_df,
            market_price_kwh_ex_btw=0.19,
            retail_price_kwh_ex_btw=-0.01,
        )
