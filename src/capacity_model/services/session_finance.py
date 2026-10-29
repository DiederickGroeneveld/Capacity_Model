from __future__ import annotations

import numpy as np
import pandas as pd


_FINANCIAL_COLUMNS = [
    "billable_energy_kwh",
    "session_market_cost_ex_btw",
    "session_turnover_ex_btw",
    "session_profit_ex_btw",
]


def add_session_financials(
    loading_profile_df: pd.DataFrame,
    *,
    market_price_kwh_ex_btw: float,
    retail_price_kwh_ex_btw: float,
) -> pd.DataFrame:
    """Add per-session turnover/cost/profit fields to the loading profile.

    Missed sessions are treated as non-billable (0 kWh billed).
    """
    if market_price_kwh_ex_btw < 0:
        raise ValueError("market_price_kwh_ex_btw must be >= 0")
    if retail_price_kwh_ex_btw < 0:
        raise ValueError("retail_price_kwh_ex_btw must be >= 0")

    result = loading_profile_df.copy()

    if result.empty:
        for column in _FINANCIAL_COLUMNS:
            result[column] = pd.Series(dtype=float)
        return result

    if "energy_kwh" not in result.columns:
        raise ValueError("loading_profile_df must contain 'energy_kwh'")

    if "session_missed" in result.columns:
        session_missed = result["session_missed"].astype(bool)
    else:
        session_missed = pd.Series(False, index=result.index)

    billable_energy_kwh = np.where(session_missed, 0.0, result["energy_kwh"].astype(float))
    session_market_cost_ex_btw = billable_energy_kwh * market_price_kwh_ex_btw
    session_turnover_ex_btw = billable_energy_kwh * retail_price_kwh_ex_btw
    session_profit_ex_btw = session_turnover_ex_btw - session_market_cost_ex_btw

    result["billable_energy_kwh"] = billable_energy_kwh
    result["session_market_cost_ex_btw"] = session_market_cost_ex_btw
    result["session_turnover_ex_btw"] = session_turnover_ex_btw
    result["session_profit_ex_btw"] = session_profit_ex_btw

    return result


def build_financial_kpis(
    loading_profile_df: pd.DataFrame,
    *,
    market_price_kwh_ex_btw: float,
    retail_price_kwh_ex_btw: float,
) -> dict[str, float]:
    """Return total turnover/cost/profit based on session-level energy."""
    financial_df = add_session_financials(
        loading_profile_df,
        market_price_kwh_ex_btw=market_price_kwh_ex_btw,
        retail_price_kwh_ex_btw=retail_price_kwh_ex_btw,
    )

    if financial_df.empty:
        return {
            "total_turnover_ex_btw": 0.0,
            "total_market_cost_ex_btw": 0.0,
            "total_profit_ex_btw": 0.0,
        }

    return {
        "total_turnover_ex_btw": float(financial_df["session_turnover_ex_btw"].sum()),
        "total_market_cost_ex_btw": float(financial_df["session_market_cost_ex_btw"].sum()),
        "total_profit_ex_btw": float(financial_df["session_profit_ex_btw"].sum()),
    }
