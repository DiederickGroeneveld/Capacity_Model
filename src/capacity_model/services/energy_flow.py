from __future__ import annotations

import math


def calculate_connection_capacity_kw(amperes: float, volt: float) -> float:
    """Calculate 3-phase connection capacity in kW.

    Formula: (sqrt(3) * A * V) / 1000
    """
    if amperes <= 0:
        raise ValueError("amperes must be > 0")
    if volt <= 0:
        raise ValueError("volt must be > 0")

    return (math.sqrt(3) * amperes * volt) / 1000
