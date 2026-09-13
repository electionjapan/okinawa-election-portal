from __future__ import annotations

# 2026-09-13 election-day production sheet.
# The user confirmed this exact Google Spreadsheet URL/ID:
# https://docs.google.com/spreadsheets/d/1s6H3je6DPCSNIzwcOQpA39t_ecISuuAjY4qT2a291is/edit?usp=sharing
#
# IMPORTANT:
# For the election-day locked build, do NOT let Streamlit Secrets or an
# environment variable silently redirect the portal to another workbook.
GOOGLE_SHEET_ID = "1s6H3je6DPCSNIzwcOQpA39t_ecISuuAjY4qT2a291is"
GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    f"{GOOGLE_SHEET_ID}/edit?usp=sharing"
)
