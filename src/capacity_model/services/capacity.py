from __future__ import annotations

import pandas as pd


def summarize_capacity(dataframe: pd.DataFrame) -> pd.DataFrame:
    summary = dataframe.copy()
    summary["gap"] = summary["capacity"] - summary["demand"]
    summary["utilization_pct"] = (summary["demand"] / summary["capacity"] * 100).round(1)
    summary["status"] = summary["gap"].apply(lambda value: "Surplus" if value >= 0 else "Shortfall")
    return summary


def build_kpis(summary: pd.DataFrame) -> dict[str, float]:
    total_capacity = float(summary["capacity"].sum())
    total_demand = float(summary["demand"].sum())
    total_gap = float(summary["gap"].sum())
    utilization_pct = round((total_demand / total_capacity * 100), 1) if total_capacity else 0.0

    return {
        "total_capacity": total_capacity,
        "total_demand": total_demand,
        "total_gap": total_gap,
        "utilization_pct": utilization_pct,
    }
