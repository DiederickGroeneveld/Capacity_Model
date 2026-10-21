import pandas as pd

from capacity_model.services.loading_profile import simulate_loading_profile_from_arrivals


def test_simulate_loading_profile_from_arrivals_creates_one_row_per_arrival() -> None:
    arrivals = pd.DataFrame(
        [
            {
                "Datum": "01/01/2026",
                "weekdag": "Thursday",
                "expected_sessions": 9,
                "trials": 1000,
                "totaal_simulated": 3,
                "00:00": 2,
                "00:01": 1,
            }
        ]
    )

    profile = simulate_loading_profile_from_arrivals(
        arrivals,
        number_of_charge_points=2,
        average_duration_min=35,
        duration_spread_min=10,
        charge_speed_kwh_per_min=1.16,
        average_kwh=40.6,
        random_seed=42,
    )

    assert len(profile) == 3
    assert {"arrival_datetime", "duration_min", "end_datetime", "energy_kwh"}.issubset(profile.columns)
    assert profile["duration_min"].ge(1).all()
    assert profile["aantal_laadpunten"].eq(2).all()
    assert profile["aantal_pistolen"].eq(4).all()
