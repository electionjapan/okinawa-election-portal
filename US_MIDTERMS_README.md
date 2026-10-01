# 2026 US Midterms module (v0.10.1)

## Main screens
- SENATE CONTROL: 100-seat national board with the 50 line and 51-seat outright-majority note.
- OVERVIEW: national map, CALL MONITOR, and race list.
- WATCH DESK: configurable state/race-type monitor. Defaults: NC, TX, ME, OH, AK; Senate only.
- SENATE / HOUSE / GOVERNOR: filtered race tables.
- RACE DETAIL: candidate totals, reporting rate, top-two gap, session history chart, API map, raw response.

## Senate baseline
The board uses the 119th Congress composition published by the U.S. Senate: 53 Republicans, 45 Democrats, 2 Independents caucusing with Democrats. The 2026 ballot baseline assumes 35 Senate contests (33 regular Class II seats plus the Ohio and Florida special elections), leaving 34 Democratic-caucus and 31 Republican holdover seats. API-confirmed calls are added to these holdovers; other races remain undecided.

## Okinawa archive mode
Okinawa 2026 live acquisition is disabled in two layers:
1. `app.py` never executes the archived live pages.
2. `portal_config.py` sets `OKINAWA_LIVE_ENABLED = False`; both Google Sheets readers refuse network acquisition even if called directly.

## Maps
No new US GeoJSON is required yet. State overview uses Plotly `USA-states`; race detail can request civicAPI-generated SVG maps. Add county or congressional-district GeoJSON later only when fully local, clickable sub-state maps are needed.
