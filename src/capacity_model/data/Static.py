from __future__ import annotations

WEEKDAY_DEFAULT_FACTORS: dict[str, float] = {
    "Monday": 1.1,
    "Tuesday": 1.1,
    "Wednesday": 1.1,
    "Thursday": 1.1,
    "Friday": 1.1,
    "Saturday": 0.8,
    "Sunday": 0.8,
}

MONTH_DEFAULT_FACTORS: dict[str, float] = {
    "Januari": 1.0,
    "Februari": 1.0,
    "Maart": 1.0,
    "April": 1.0,
    "Mei": 1.0,
    "Juni": 1.0,
    "Juli": 1.0,
    "Augustus": 1.0,
    "September": 1.0,
    "Oktober": 1.0,
    "November": 1.0,
    "December": 1.0,
}