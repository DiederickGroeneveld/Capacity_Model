from __future__ import annotations

from typing import Sequence

import pandas as pd

from capacity_model.services.distributions import combine_normal_distributions
from capacity_model.services.factors import apply_scalar_factor


def build_probability_curve_dataframe(
    means: Sequence[float],
    std_devs: Sequence[float],
    weights: Sequence[float] | None,
    per_minute: bool,
    active_factor: float,
    num_points: int = 500,
    std_range: float = 4.0,
) -> tuple[pd.DataFrame, str]:
    if per_minute:
        x_values = [minute / 60.0 for minute in range(24 * 60)]
        x, y = combine_normal_distributions(
            means=means,
            std_devs=std_devs,
            weights=weights,
            x_values=x_values,
        )
        adjusted_y = apply_scalar_factor(y, active_factor)
        dataframe = pd.DataFrame(
            {
                "Minuut in dag": list(range(24 * 60)),
                "Uur in dag": x,
                "probability": adjusted_y,
            }
        )
        return dataframe, "Uur in dag"

    x, y = combine_normal_distributions(
        means=means,
        std_devs=std_devs,
        weights=weights,
        num_points=num_points,
        std_range=std_range,
    )
    adjusted_y = apply_scalar_factor(y, active_factor)
    dataframe = pd.DataFrame({"x": x, "probability": adjusted_y})
    return dataframe, "x"
