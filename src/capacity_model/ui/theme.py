from __future__ import annotations

GOASE_COLORS: dict[str, str] = {
    "green": "#4A7B38",
    "green_dark": "#2F5A2C",
    "yellow": "#F7B500",
    "yellow_light": "#FFD56A",
    "white": "#FFFFFF",
    "text_dark": "#1E2A1E",
}


def apply_brand_theme(st_module) -> None:
    st_module.markdown(
        f"""
        <style>
            .stApp {{
                color: {GOASE_COLORS['text_dark']};
            }}

            div[data-testid="stMetricValue"] {{
                color: {GOASE_COLORS['green_dark']};
            }}

            .stButton > button {{
                background-color: {GOASE_COLORS['green']};
                color: {GOASE_COLORS['white']};
                border: 1px solid {GOASE_COLORS['green_dark']};
            }}

            .stButton > button:hover {{
                border-color: {GOASE_COLORS['yellow']};
                color: {GOASE_COLORS['yellow_light']};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_curve_figure(figure) -> None:
    figure.update_traces(line=dict(color=GOASE_COLORS["yellow"], width=3))
    figure.update_layout(
        font_color=GOASE_COLORS["text_dark"],
        title_font_color=GOASE_COLORS["green_dark"],
        xaxis=dict(gridcolor="#E8EFE6"),
        yaxis=dict(gridcolor="#E8EFE6"),
    )
