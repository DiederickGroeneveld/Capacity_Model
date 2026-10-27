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
    assert {"used_pistol", "session_missed", "pistol_1_in_use", "pistol_2_in_use", "pistol_3_in_use", "pistol_4_in_use"}.issubset(
        profile.columns
    )
    assert {"missed_at_arrival", "minutes_until_next_available", "session_in_progress_within_threshold", "recaptured_session", "recapture_rate", "in_progress_threshold_min"}.issubset(
        profile.columns
    )
    assert profile["session_missed"].sum() == 0
    assert profile["missed_sessions_at_arrival_time"].eq(0).all()
    assert profile["recapture_rate"].eq(0.2).all()
    assert profile["in_progress_threshold_min"].eq(10.0).all()


def test_simulate_loading_profile_marks_missed_sessions_when_no_pistol_available() -> None:
    arrivals = pd.DataFrame(
        [
            {
                "Datum": "01/01/2026",
                "weekdag": "Thursday",
                "expected_sessions": 9,
                "trials": 1000,
                "totaal_simulated": 3,
                "00:00": 3,
            }
        ]
    )

    profile = simulate_loading_profile_from_arrivals(
        arrivals,
        number_of_charge_points=1,
        average_duration_min=35,
        duration_spread_min=0,
        charge_speed_kwh_per_min=1.16,
        average_kwh=40.6,
        random_seed=42,
    )

    assert len(profile) == 3
    assert profile["aantal_pistolen"].eq(2).all()
    assert profile["session_missed"].sum() == 1

    missed_rows = profile.loc[profile["session_missed"]]
    assert missed_rows["used_pistol"].eq("missed").all()
    assert missed_rows["missed_sessions_at_arrival_time"].eq(1).all()

    served_rows = profile.loc[~profile["session_missed"]]
    assert served_rows["used_pistol"].isin(["pistol_1", "pistol_2"]).all()
    assert served_rows[["pistol_1_in_use", "pistol_2_in_use"]].sum(axis=1).eq(1).all()
    assert missed_rows["missed_at_arrival"].all()
    assert missed_rows["session_in_progress_within_threshold"].eq(False).all()
