from __future__ import annotations

# 2026-10-01: Okinawa live operation has ended. Keep this False to prevent
# any Google Sheets acquisition even if an archived live module is invoked.
OKINAWA_LIVE_ENABLED = False
GOOGLE_SHEET_ID = ""

def get_google_sheet_id() -> str:
    return ""
