from dataclasses import dataclass
import os

import streamlit as st


@dataclass(frozen=True)
class Settings:
    app_title: str = "Capacity Model"
    environment: str = "local"


@st.cache_resource
def get_settings() -> Settings:
    return Settings(
        app_title=os.getenv("APP_TITLE", "Capacity Model"),
        environment=os.getenv("APP_ENV", "local"),
    )
