"""Domain services for the Capacity Model app."""

from .arrival_simulation import simulate_daily_arrivals, simulate_daily_arrivals_from_probability_table
from .curve_data import build_probability_curve_dataframe
from .daily_probability_table import build_daily_probability_table
from .distributions import combine_normal_distributions
from .energy_flow import (
	apply_battery_constraints_to_loading_profile,
	build_cumulative_energy_flow_dataframe,
	calculate_connection_capacity_kw,
)
from .factors import apply_scalar_factor, resolve_active_factor
from .loading_profile import simulate_loading_profile_from_arrivals
from .session_finance import add_session_financials, build_financial_kpis

__all__ = [
	"combine_normal_distributions",
	"build_daily_probability_table",
	"simulate_daily_arrivals_from_probability_table",
	"simulate_daily_arrivals",
	"simulate_loading_profile_from_arrivals",
	"build_cumulative_energy_flow_dataframe",
	"calculate_connection_capacity_kw",
	"apply_battery_constraints_to_loading_profile",
	"resolve_active_factor",
	"apply_scalar_factor",
	"build_probability_curve_dataframe",
	"add_session_financials",
	"build_financial_kpis",
]
