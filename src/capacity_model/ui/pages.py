from __future__ import annotations

import base64
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from capacity_model.config import Settings
from capacity_model.data import MONTH_DEFAULT_FACTORS, WEEKDAY_DEFAULT_FACTORS
from capacity_model.data.loaders import load_sample_data, load_uploaded_data
from capacity_model.services.arrival_simulation import simulate_daily_arrivals_from_probability_table
from capacity_model.services.curve_data import build_probability_curve_dataframe
from capacity_model.services.daily_probability_table import build_daily_probability_table
from capacity_model.services.energy_flow import (
    apply_battery_constraints_to_loading_profile,
    build_cumulative_energy_flow_dataframe,
    calculate_connection_capacity_kw,
)
from capacity_model.services.factors import resolve_active_factor
from capacity_model.services.loading_profile import simulate_loading_profile_from_arrivals
from capacity_model.services.session_finance import add_session_financials, build_financial_kpis
from capacity_model.ui.theme import apply_brand_theme, style_curve_figure


DEFAULT_LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "company_logo.png"

def render_home_page(settings: Settings) -> None:
    st.set_page_config(page_title=settings.app_title, layout="wide")
    apply_brand_theme(st)

    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "dashboard"

    if st.session_state["active_view"] == "probability_data":
        _render_probability_data_page()
        return

    st.title(settings.app_title)
    st.caption(f"Environment: {settings.environment}")
    st.write("Use the sample dataset or upload a CSV to explore capacity vs. demand.")

    with st.sidebar:
        _render_company_logo()
        st.header("Data source")
        uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
        selected_team = st.text_input("Filter team", placeholder="Optional")
        st.divider()
        st.header("Probability curve inputs")
        means_raw = st.text_input("Means (hours)", value="8,12,18")
        std_raw = st.text_input("Std devs (hours)", value="1.0,1.5,2.0")
        weights_raw = st.text_input("Weights (optional)", value="0.3,0.4,0.3")
        per_minute = st.checkbox("One value per minute", value=True)
        st.subheader("Week verdeling")
        weekday_factors = {
            day: st.number_input(
                day,
                min_value=0.0,
                value=default_value,
                step=0.1,
                format="%.2f",
                key=f"weekday_{day.lower()}",
            )
            for day, default_value in WEEKDAY_DEFAULT_FACTORS.items()
        }

        st.subheader("Maand verdeling")
        month_factors = {
            month: st.number_input(
                month,
                min_value=0.0,
                value=default_value,
                step=0.1,
                format="%.2f",
                key=f"month_{month.lower()}",
            )
            for month, default_value in MONTH_DEFAULT_FACTORS.items()
        }
        st.divider()
        selected_weekday = st.selectbox("Gebruik weekfactor van", list(weekday_factors.keys()), index=0)
        selected_month = st.selectbox("Gebruik maandfactor van", list(month_factors.keys()), index=0)
        run = st.button("Build curve")
        st.divider()
        start_date = st.date_input("Start date", value=date.today())
        end_date = st.date_input("End date", value=date.today() + timedelta(days=30))
        expected_sessions = int(
            st.number_input(
                "Expected amount of sessions",
                min_value=1,
                value=9,
                step=1,
            )
        )
        trials = int(
            st.number_input(
                "Amount of trials",
                min_value=1,
                value=1000,
                step=1,
            )
        )
        st.divider()
        st.header("Charging profile inputs")
        number_of_charge_points = int(
            st.number_input(
                "Aantal laadpunten",
                min_value=1,
                value=2,
                step=1,
            )
        )
        st.caption(f"Aantal pistolen (2 per paal): {number_of_charge_points * 2}")
        average_duration_min = float(
            st.number_input(
                "Gemiddelde duur (min)",
                min_value=1.0,
                value=35.0,
                step=1.0,
            )
        )
        duration_spread_min = float(
            st.number_input(
                "Spreiding (min)",
                min_value=0.0,
                value=10.0,
                step=1.0,
            )
        )
        charge_speed_kwh_per_min = float(
            st.number_input(
                "Laad snelheid (kWh/minuut)",
                min_value=0.01,
                value=1.16,
                step=0.01,
                format="%.2f",
            )
        )
        average_kwh = float(
            st.number_input(
                "Gemiddelde kWh",
                min_value=0.1,
                value=40.6,
                step=0.1,
                format="%.1f",
            )
        )
        recapture_rate = float(
            st.number_input(
                "Recapture rate",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.01,
                format="%.2f",
            )
        )
        in_progress_threshold_min = float(
            st.number_input(
                "Time to end of session in progress (min)",
                min_value=0.0,
                value=10.0,
                step=1.0,
                format="%.1f",
            )
        )
        amperes = float(
            st.number_input(
                "Amperes",
                min_value=1.0,
                value=80.0,
                step=1.0,
                format="%.1f",
            )
        )
        volt = float(
            st.number_input(
                "Volt",
                min_value=1.0,
                value=400.0,
                step=1.0,
                format="%.1f",
            )
        )
        battery_size_kwh = float(
            st.number_input(
                "Battery size (kWh)",
                min_value=0.1,
                value=260.0,
                step=1.0,
                format="%.1f",
            )
        )
        market_price_kwh_ex_btw = float(
            st.number_input(
                "Market price KWH ex. btw",
                min_value=0.0,
                value=0.19,
                step=0.01,
                format="%.2f",
            )
        )
        retail_price_kwh_ex_btw = float(
            st.number_input(
                "Retail price KWH ex. btw",
                min_value=0.0,
                value=0.59,
                step=0.01,
                format="%.2f",
            )
        )
        connection_capacity_kw = calculate_connection_capacity_kw(amperes, volt)
        st.metric("Connection capacity (kW)", f"{connection_capacity_kw:.2f}")
        
    try:
        raw_data = load_uploaded_data(uploaded_file) if uploaded_file else load_sample_data()
    except ValueError as error:
        st.error(str(error))
        return

    filtered_data = _filter_data(raw_data, selected_team)
    st.session_state["summary_df"] = filtered_data
    kpi_container = st.container()

    _render_probability_curve(
        run,
        start_date,
        end_date,
        expected_sessions,
        trials,
        number_of_charge_points,
        average_duration_min,
        duration_spread_min,
        charge_speed_kwh_per_min,
        average_kwh,
        recapture_rate,
        in_progress_threshold_min,
        connection_capacity_kw,
        amperes,
        volt,
        battery_size_kwh,
        market_price_kwh_ex_btw,
        retail_price_kwh_ex_btw,
        means_raw,
        std_raw,
        weights_raw,
        per_minute,
        weekday_factors,
        month_factors,
        selected_weekday,
        selected_month,
    )

    total_sessions = _get_total_sessions(st.session_state.get("loading_profile_df"))
    missed_sessions_pistol, missed_sessions_battery = _get_missed_sessions_by_reason(
        st.session_state.get("loading_profile_df")
    )
    kpis = build_financial_kpis(
        st.session_state.get("loading_profile_df", pd.DataFrame()),
        market_price_kwh_ex_btw=market_price_kwh_ex_btw,
        retail_price_kwh_ex_btw=retail_price_kwh_ex_btw,
    )
    with kpi_container:
        _render_kpis(kpis, total_sessions, missed_sessions_pistol, missed_sessions_battery)


def _parse_float_list(raw: str, label: str) -> list[float]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError(f"{label} cannot be empty.")
    return [float(value) for value in values]


def _render_company_logo() -> None:
    if DEFAULT_LOGO_PATH.exists():
        logo_bytes = DEFAULT_LOGO_PATH.read_bytes()
        logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")
        st.markdown(
            f"""
            <div style="
                background-color:#2F5A2C;
                border-radius:12px;
                padding:12px;
                margin-bottom:8px;
            ">
                <img src="data:image/png;base64,{logo_b64}" style="width:100%;height:auto;display:block;" />
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()


def _render_probability_curve(
    run: bool,
    start_date: date,
    end_date: date,
    expected_sessions: int,
    trials: int,
    number_of_charge_points: int,
    average_duration_min: float,
    duration_spread_min: float,
    charge_speed_kwh_per_min: float,
    average_kwh: float,
    recapture_rate: float,
    in_progress_threshold_min: float,
    connection_capacity_kw: float,
    amperes: float,
    volt: float,
    battery_size_kwh: float,
    market_price_kwh_ex_btw: float,
    retail_price_kwh_ex_btw: float,
    means_raw: str,
    std_raw: str,
    weights_raw: str,
    per_minute: bool,
    weekday_factors: dict[str, float],
    month_factors: dict[str, float],
    selected_weekday: str,
    selected_month: str,
) -> None:
    header_col, button_col = st.columns([4, 1])
    with header_col:
        st.subheader("Combined probability curve")
    with button_col:
        st.write("")
        if st.button("Open data table", key="open_probability_data_table"):
            st.session_state["active_view"] = "probability_data"
            st.rerun()

    if not run:
        stored_curve_df = st.session_state.get("curve_df")
        stored_energy_flow_df = st.session_state.get("energy_flow_df")
        stored_x_column = st.session_state.get("curve_x_column")

        if (
            isinstance(stored_curve_df, pd.DataFrame)
            and not stored_curve_df.empty
            and isinstance(stored_energy_flow_df, pd.DataFrame)
            and not stored_energy_flow_df.empty
            and isinstance(stored_x_column, str)
            and stored_x_column in stored_curve_df.columns
        ):
            title_prefix = str(st.session_state.get("curve_title_prefix", "Kans curve"))
            curve_weekday = str(st.session_state.get("curve_selected_weekday", selected_weekday))
            curve_month = str(st.session_state.get("curve_selected_month", selected_month))
            week_factor = float(st.session_state.get("curve_active_week_factor", 1.0))
            month_factor = float(st.session_state.get("curve_active_month_factor", 1.0))
            active_factor = float(st.session_state.get("curve_active_factor", 1.0))
            stored_start_date = str(st.session_state.get("curve_start_date", ""))
            stored_end_date = str(st.session_state.get("curve_end_date", ""))

            st.caption("Showing last built curve. Click 'Build curve' to recalculate.")

            figure = px.line(
                stored_curve_df,
                x=stored_x_column,
                y="probability",
                title=f"{title_prefix} ({curve_weekday} x {curve_month})",
                labels={"probability": "Kans op aankomst auto"},
            )
            style_curve_figure(figure)

            st.caption(
                f"Applied factor = week({curve_weekday}: {week_factor:.2f}) x "
                f"month({curve_month}: {month_factor:.2f}) = {active_factor:.2f}"
            )
            if stored_start_date and stored_end_date:
                st.caption(f"Date range: {stored_start_date} → {stored_end_date}")

            st.plotly_chart(figure, use_container_width=True)

            st.subheader("Cumulative energy graph")
            energy_figure = px.line(
                stored_energy_flow_df,
                x="timestamp",
                y="battery_remaining_kwh",
                title="Battery pack remaining energy over time",
                labels={
                    "timestamp": "Time",
                    "battery_remaining_kwh": "Battery remaining (kWh)",
                },
            )
            style_curve_figure(energy_figure)
            st.plotly_chart(energy_figure, use_container_width=True)
            return

        st.info("Set inputs in the sidebar and click 'Build curve'.")
        return

    if end_date < start_date:
        st.error("End date must be on or after start date.")
        return

    try:
        means = _parse_float_list(means_raw, "Means")
        std_devs = _parse_float_list(std_raw, "Std devs")
        weights = _parse_float_list(weights_raw, "Weights") if weights_raw.strip() else None
        active_week_factor, active_month_factor, active_factor = resolve_active_factor(
            weekday_factors=weekday_factors,
            month_factors=month_factors,
            selected_weekday=selected_weekday,
            selected_month=selected_month,
        )

        curve_df, x_column = build_probability_curve_dataframe(
            means=means,
            std_devs=std_devs,
            weights=weights,
            per_minute=per_minute,
            active_factor=active_factor,
            num_points=500,
            std_range=4.0,
        )

        title_prefix = "Probability per minute van de dag" if per_minute else "Kans curve"
        st.session_state["curve_df"] = curve_df
        st.session_state["curve_x_column"] = x_column
        st.session_state["curve_title_prefix"] = title_prefix
        st.session_state["curve_selected_weekday"] = selected_weekday
        st.session_state["curve_selected_month"] = selected_month
        st.session_state["curve_active_week_factor"] = active_week_factor
        st.session_state["curve_active_month_factor"] = active_month_factor
        st.session_state["curve_active_factor"] = active_factor
        st.session_state["curve_start_date"] = start_date.isoformat()
        st.session_state["curve_end_date"] = end_date.isoformat()

        figure = px.line(
            curve_df,
            x=x_column,
            y="probability",
            title=f"{title_prefix} ({selected_weekday} x {selected_month})",
            labels={"probability": "Kans op aankomst auto"},
        )

        style_curve_figure(figure)

        st.caption(
            f"Applied factor = week({selected_weekday}: {active_week_factor:.2f}) x "
            f"month({selected_month}: {active_month_factor:.2f}) = {active_factor:.2f}"
        )
        st.caption(f"Date range: {start_date.isoformat()} → {end_date.isoformat()}")

        probability_table_df = build_daily_probability_table(
            start_date=start_date,
            end_date=end_date,
            means=means,
            std_devs=std_devs,
            weights=weights,
            weekday_factors=weekday_factors,
            month_factors=month_factors,
        )
        st.session_state["probability_table_df"] = probability_table_df
        st.session_state["simulated_arrivals_df"] = simulate_daily_arrivals_from_probability_table(
            probability_table_df,
            expected_sessions=expected_sessions,
            trials=trials,
            random_seed=42,
        )
        loading_profile_df = simulate_loading_profile_from_arrivals(
            st.session_state["simulated_arrivals_df"],
            number_of_charge_points=number_of_charge_points,
            average_duration_min=average_duration_min,
            duration_spread_min=duration_spread_min,
            charge_speed_kwh_per_min=charge_speed_kwh_per_min,
            average_kwh=average_kwh,
            recapture_rate=recapture_rate,
            in_progress_threshold_min=in_progress_threshold_min,
            random_seed=42,
        )
        loading_profile_df = apply_battery_constraints_to_loading_profile(
            loading_profile_df,
            battery_size_kwh=battery_size_kwh,
            connection_capacity_kw=connection_capacity_kw,
            session_draw_kwh_per_min=charge_speed_kwh_per_min,
        )
        loading_profile_df = add_session_financials(
            loading_profile_df,
            market_price_kwh_ex_btw=market_price_kwh_ex_btw,
            retail_price_kwh_ex_btw=retail_price_kwh_ex_btw,
        )
        loading_profile_df["connection_capacity_kw"] = round(connection_capacity_kw, 3)
        loading_profile_df["amperes"] = amperes
        loading_profile_df["volt"] = volt
        loading_profile_df["battery_size_kwh"] = battery_size_kwh
        loading_profile_df["market_price_kwh_ex_btw"] = market_price_kwh_ex_btw
        loading_profile_df["retail_price_kwh_ex_btw"] = retail_price_kwh_ex_btw
        st.session_state["loading_profile_df"] = loading_profile_df

        energy_flow_df = build_cumulative_energy_flow_dataframe(
            st.session_state["loading_profile_df"],
            start_date=pd.Timestamp(start_date),
            end_date=pd.Timestamp(end_date),
            battery_size_kwh=battery_size_kwh,
            connection_capacity_kw=connection_capacity_kw,
            session_draw_kwh_per_min=charge_speed_kwh_per_min,
        )
        energy_flow_df["market_price_kwh_ex_btw"] = market_price_kwh_ex_btw
        energy_flow_df["retail_price_kwh_ex_btw"] = retail_price_kwh_ex_btw
        st.session_state["energy_flow_df"] = energy_flow_df

        st.plotly_chart(figure, use_container_width=True)

        st.subheader("Cumulative energy graph")
        energy_figure = px.line(
            energy_flow_df,
            x="timestamp",
            y="battery_remaining_kwh",
            title="Battery pack remaining energy over time",
            labels={
                "timestamp": "Time",
                "battery_remaining_kwh": "Battery remaining (kWh)",
            },
        )
        style_curve_figure(energy_figure)
        st.plotly_chart(energy_figure, use_container_width=True)
    except ValueError as error:
        st.error(f"Curve input error: {error}")


def _render_probability_data_page() -> None:
    st.title("Probability data table")
    if st.button("← Back to dashboard", key="back_to_dashboard"):
        st.session_state["active_view"] = "dashboard"
        st.rerun()

    probability_table_df = st.session_state.get("probability_table_df")
    simulated_arrivals_df = st.session_state.get("simulated_arrivals_df")
    loading_profile_df = st.session_state.get("loading_profile_df")

    st.markdown("### Probability curve dataset")
    if isinstance(probability_table_df, pd.DataFrame) and not probability_table_df.empty:
        st.write(f"Rows: {len(probability_table_df)}")
        st.dataframe(probability_table_df, use_container_width=True)
        st.download_button(
            "Download probability table (CSV)",
            data=probability_table_df.to_csv(index=False).encode("utf-8"),
            file_name="probability_table_dataset.csv",
            mime="text/csv",
        )
    else:
        st.info("No curve dataset yet. Go to Dashboard and click 'Build curve'.")

    st.markdown("### Simulated arrivals dataset")
    if isinstance(simulated_arrivals_df, pd.DataFrame) and not simulated_arrivals_df.empty:
        st.write(f"Rows: {len(simulated_arrivals_df)}")
        st.dataframe(simulated_arrivals_df, use_container_width=True)
        st.download_button(
            "Download simulated arrivals (CSV)",
            data=simulated_arrivals_df.to_csv(index=False).encode("utf-8"),
            file_name="simulated_arrivals_dataset.csv",
            mime="text/csv",
        )
    else:
        st.info("No simulated arrivals dataset yet. Go to Dashboard and click 'Build curve'.")

    st.markdown("### Loading profile dataset")
    if isinstance(loading_profile_df, pd.DataFrame) and not loading_profile_df.empty:
        mu_duration = float(loading_profile_df["duration_min"].mean())
        sigma_duration = float(loading_profile_df["duration_min"].std(ddof=0))

        kpi_col_1, kpi_col_2 = st.columns(2)
        kpi_col_1.metric("μ duur (min)", f"{mu_duration:.2f}")
        kpi_col_2.metric("σ duur (min)", f"{sigma_duration:.2f}")

        st.write(f"Rows: {len(loading_profile_df)}")
        st.dataframe(loading_profile_df, use_container_width=True)
        st.download_button(
            "Download loading profile (CSV)",
            data=loading_profile_df.to_csv(index=False).encode("utf-8"),
            file_name="loading_profile_dataset.csv",
            mime="text/csv",
        )
    else:
        st.info("No loading profile dataset yet. Go to Dashboard and click 'Build curve'.")


def _filter_data(dataframe: pd.DataFrame, selected_team: str) -> pd.DataFrame:
    if not selected_team:
        return dataframe

    team_mask = dataframe["team"].str.contains(selected_team, case=False, na=False)
    return dataframe.loc[team_mask].reset_index(drop=True)


def _get_missed_sessions_by_reason(loading_profile_df: object) -> tuple[int, int]:
    if not isinstance(loading_profile_df, pd.DataFrame) or loading_profile_df.empty:
        return 0, 0

    if "missed_reason" in loading_profile_df.columns:
        reasons = loading_profile_df["missed_reason"].astype(str)
        missed_pistol = int((reasons == "pistol_unavailable").sum())
        missed_battery = int((reasons == "battery_empty").sum())
        return missed_pistol, missed_battery

    if "session_missed_by_battery" in loading_profile_df.columns and "session_missed" in loading_profile_df.columns:
        missed_battery = int(loading_profile_df["session_missed_by_battery"].astype(bool).sum())
        missed_total = int(loading_profile_df["session_missed"].astype(bool).sum())
        missed_pistol = max(0, missed_total - missed_battery)
        return missed_pistol, missed_battery

    if "session_missed" in loading_profile_df.columns:
        return int(loading_profile_df["session_missed"].astype(bool).sum()), 0

    return 0, 0


def _get_total_sessions(loading_profile_df: object) -> int:
    if not isinstance(loading_profile_df, pd.DataFrame) or loading_profile_df.empty:
        return 0

    return int(len(loading_profile_df))


def _render_kpis(
    kpis: dict[str, float],
    total_sessions: int,
    missed_sessions_pistol: int,
    missed_sessions_battery: int,
) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total turnover ex. btw", f"€ {kpis['total_turnover_ex_btw']:,.2f}")
    col2.metric("Total profit ex. btw", f"€ {kpis['total_profit_ex_btw']:,.2f}")
    col3.metric("Total Sessions", f"{total_sessions}")
    col4.metric("Missed (pistol)", f"{missed_sessions_pistol}")
    col5.metric("Missed (battery)", f"{missed_sessions_battery}")
