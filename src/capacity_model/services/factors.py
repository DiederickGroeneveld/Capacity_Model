from __future__ import annotations

from typing import Sequence


def resolve_active_factor(
    weekday_factors: dict[str, float],
    month_factors: dict[str, float],
    selected_weekday: str,
    selected_month: str,
) -> tuple[float, float, float]:
    week_factor = float(weekday_factors[selected_weekday])
    month_factor = float(month_factors[selected_month])
    return week_factor, month_factor, week_factor * month_factor


def apply_scalar_factor(values: Sequence[float], factor: float) -> list[float]:
    return [float(value) * factor for value in values]
