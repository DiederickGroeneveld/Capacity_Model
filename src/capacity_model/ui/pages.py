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
from capacity_model.services.capacity import build_kpis, summarize_capacity
from capacity_model.services.curve_data import build_probability_curve_dataframe
from capacity_model.services.daily_probability_table import build_daily_probability_table
from capacity_model.services.factors import resolve_active_factor
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
                value=100,
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
        
    try:
        raw_data = load_uploaded_data(uploaded_file) if uploaded_file else load_sample_data()
    except ValueError as error:
        st.error(str(error))
        return

    filtered_data = _filter_data(raw_data, selected_team)
    summary = summarize_capacity(filtered_data)
    kpis = build_kpis(summary)
    st.session_state["summary_df"] = summary

    _render_kpis(kpis)
    _render_probability_curve(
        run,
        start_date,
        end_date,
        expected_sessions,
        trials,
        means_raw,
        std_raw,
        weights_raw,
        per_minute,
        weekday_factors,
        month_factors,
        selected_weekday,
        selected_month,
    )


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

        st.plotly_chart(figure, use_container_width=True)
    except ValueError as error:
        st.error(f"Curve input error: {error}")


def _render_probability_data_page() -> None:
    st.title("Probability data table")
    if st.button("← Back to dashboard", key="back_to_dashboard"):
        st.session_state["active_view"] = "dashboard"
        st.rerun()

    probability_table_df = st.session_state.get("probability_table_df")
    simulated_arrivals_df = st.session_state.get("simulated_arrivals_df")

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


def _filter_data(dataframe: pd.DataFrame, selected_team: str) -> pd.DataFrame:
    if not selected_team:
        return dataframe

    team_mask = dataframe["team"].str.contains(selected_team, case=False, na=False)
    return dataframe.loc[team_mask].reset_index(drop=True)


def _render_kpis(kpis: dict[str, float]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Capacity", f"{kpis['total_capacity']:,.0f}")
    col2.metric("Total Demand", f"{kpis['total_demand']:,.0f}")
    col3.metric("Net Gap", f"{kpis['total_gap']:,.0f}")
    col4.metric("Utilization", f"{kpis['utilization_pct']:.1f}%")
