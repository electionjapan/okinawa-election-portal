from __future__ import annotations

import os

DEFAULT_GOOGLE_SHEET_ID = "1s6H3je6DPCSNIzwcOQpA39t_ecISuuAjY4qT2a291is"

def _secret_value():
    try:
        import streamlit as st
        value = st.secrets.get("GOOGLE_SHEET_ID", "")
        return str(value).strip() if value else ""
    except Exception:
        return ""

def get_google_sheet_id() -> str:
    # Streamlit Secrets > environment variable > packaged fallback.
    return _secret_value() or os.getenv("GOOGLE_SHEET_ID", "").strip() or DEFAULT_GOOGLE_SHEET_ID

GOOGLE_SHEET_ID = get_google_sheet_id()
