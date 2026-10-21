from __future__ import annotations

from io import StringIO

import pandas as pd

REQUIRED_COLUMNS = {"team", "period", "capacity", "demand"}


def load_sample_data() -> pd.DataFrame:
    sample = StringIO(
        """team,period,capacity,demand
Operations,2026-Q1,120,100
Operations,2026-Q2,115,135
Engineering,2026-Q1,150,140
Engineering,2026-Q2,145,165
Support,2026-Q1,90,88
Support,2026-Q2,92,96
"""
    )
    return pd.read_csv(sample)


def load_uploaded_data(uploaded_file) -> pd.DataFrame:
    dataframe = pd.read_csv(uploaded_file)
    missing_columns = REQUIRED_COLUMNS.difference(dataframe.columns)

    if missing_columns:
        missing_str = ", ".join(sorted(missing_columns))
        raise ValueError(f"Uploaded file is missing required columns: {missing_str}")

    return dataframe

