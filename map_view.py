from __future__ import annotations

from html import escape
from typing import Mapping

import pandas as pd
import plotly.graph_objects as go

RED = "#C93238"
BLUE = "#1675B9"
RED_LIGHT = "#F4DBDD"
BLUE_LIGHT = "#DDEAF6"
GRAY = "#8E8E8E"
GRAY_LIGHT = "#EFEFEF"
TIE_GRAY = "#BDBDBD"
OTHER_GRAY = "#E3E3E3"
BLUE_BLOC_ATTRS = {"オール沖縄系", "革新系（2014年以前）"}

ZOOM_PRESETS = {
    "全県": {"center": {"lon": 127.05, "lat": 25.65}, "zoom": 4.25},
    "沖縄本島": {"center": {"lon": 127.82, "lat": 26.45}, "zoom": 7.05},
    "北部": {"center": {"lon": 128.02, "lat": 26.67}, "zoom": 8.0},
    "中南部": {"center": {"lon": 127.73, "lat": 26.20}, "zoom": 8.65},
    "久米島・慶良間": {"center": {"lon": 126.82, "lat": 26.10}, "zoom": 7.0},
    "宮古": {"center": {"lon": 125.25, "lat": 24.80}, "zoom": 8.0},
    "八重山": {"center": {"lon": 123.75, "lat": 24.40}, "zoom": 7.25},
    "大東": {"center": {"lon": 131.27, "lat": 25.90}, "zoom": 8.2},
}


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02X}" for v in rgb)


def blend(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))


def lead_fill_color(attribute: str, lead_points: float, reported_votes: float) -> str:
    if reported_votes <= 0:
        return GRAY_LIGHT
    if attribute == "同数" or abs(float(lead_points or 0)) < 1e-12:
        return TIE_GRAY
    t = min(abs(float(lead_points or 0)) / 25.0, 1.0)
    if attribute == "保守系":
        return blend(RED_LIGHT, RED, t)
    if attribute in BLUE_BLOC_ATTRS:
        return blend(BLUE_LIGHT, BLUE, t)
    return OTHER_GRAY


def winner_take_all_color(attribute: str, reported_votes: float) -> str:
    if reported_votes <= 0:
        return GRAY_LIGHT
    if attribute == "同数":
        return TIE_GRAY
    if attribute == "保守系":
        return RED
    if attribute in BLUE_BLOC_ATTRS:
        return BLUE
    return GRAY


def _safe_float(value, default=0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _fmt_int(value) -> str:
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return "—"


def _fmt_pct(value, digits=1) -> str:
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    try:
        return f"{float(value):.{digits}f}%"
    except Exception:
        return "—"


def _candidate_rows(current: pd.DataFrame, code: str) -> list[dict]:
    d = current[current["municipality_code"].astype(str) == str(code)].copy()
    if d.empty:
        return []
    d = d.sort_values(["current_votes", "candidate_id"], ascending=[False, True])
    total = float(d["current_votes"].sum())
    out = []
    for _, r in d.iterrows():
        votes = float(r.get("current_votes", 0) or 0)
        pct = (100 * votes / total) if total > 0 else 0.0
        out.append(
            {
                "name": str(r.get("candidate_name", "")),
                "votes": votes,
                "pct": pct,
                "attribute": str(r.get("attribute", "")),
            }
        )
    return out


def build_hover_text(row: pd.Series, current: pd.DataFrame, prev_context: Mapping[str, dict] | None = None) -> str:
    code = str(row.get("municipality_code", ""))
    name = escape(str(row.get("municipality_name", "")))
    status = escape(str(row.get("status", "")))
    reporting = _fmt_pct(row.get("reporting_pct"), 1)
    leader = escape(str(row.get("leader_name", "未開票")))
    lead_votes = _fmt_int(row.get("lead_votes"))
    lead_points = _fmt_pct(row.get("lead_points"), 1)

    prev_line = ""
    if prev_context and code in prev_context:
        p = prev_context[code]
        prev_line = (
            f"<br><span style='color:#666'>前回2022：{escape(str(p.get('winner_name','')))} "
            f"{_fmt_pct(p.get('point_diff'), 1)}差で勝利</span>"
        )

    lines = [f"<b>{name}</b>{prev_line}"]
    cands = _candidate_rows(current, code)
    if cands and sum(x["votes"] for x in cands) > 0:
        lines.append(f"<br><b>首位：{leader}</b>（{lead_points} / {lead_votes}票リード）")
        for c in cands:
            lines.append(
                f"<br>{escape(c['name'])}　{_fmt_int(c['votes'])}票　{c['pct']:.1f}%"
            )
    else:
        lines.append("<br>未開票")
    lines.append(f"<br>開票率：{reporting}　{status}")
    return "".join(lines)


def _fixed_polygon_trace(feature: dict, code: str, color: str, hover_text: str):
    one_geojson = {"type": "FeatureCollection", "features": [feature]}
    return go.Choroplethmapbox(
        geojson=one_geojson,
        locations=[str(code)],
        z=[1],
        featureidkey="properties.municipality_code",
        colorscale=[[0, color], [1, color]],
        zmin=0,
        zmax=1,
        marker_opacity=0.86,
        marker_line_width=0.7,
        marker_line_color="#FFFFFF",
        customdata=[hover_text],
        hovertemplate="%{customdata}<extra></extra>",
        showscale=False,
        name="",
    )


def _neutral_base_trace(geojson: dict, codes: list[str], hover_texts: list[str]):
    return go.Choroplethmapbox(
        geojson=geojson,
        locations=codes,
        z=[1] * len(codes),
        featureidkey="properties.municipality_code",
        colorscale=[[0, "#F3F3F3"], [1, "#F3F3F3"]],
        zmin=0,
        zmax=1,
        marker_opacity=0.72,
        marker_line_width=0.7,
        marker_line_color="#C9C9C9",
        customdata=hover_texts,
        hovertemplate="%{customdata}<extra></extra>",
        showscale=False,
        name="",
    )


def build_map_figure(
    geojson: dict,
    msum: pd.DataFrame,
    current: pd.DataFrame,
    mode: str,
    zoom_preset: str = "全県",
    show_labels: bool = False,
    prev_context: Mapping[str, dict] | None = None,
    height: int = 690,
):
    m = msum.copy()
    m["municipality_code"] = m["municipality_code"].astype(str)
    rows = {str(r["municipality_code"]): r for _, r in m.iterrows()}
    fig = go.Figure()

    feature_by_code = {
        str(f["properties"]["municipality_code"]): f for f in geojson["features"]
    }
    feature_props = {code: f["properties"] for code, f in feature_by_code.items()}

    hover_by_code = {
        code: build_hover_text(row, current, prev_context=prev_context) for code, row in rows.items()
    }

    if mode in {"得票シェア", "国盗り"}:
        for code, row in rows.items():
            reported_votes = _safe_float(row.get("reported_votes", 0), 0)
            attr = str(row.get("leader_attribute", ""))
            lead_points = _safe_float(row.get("lead_points", 0), 0)
            if mode == "得票シェア":
                color = lead_fill_color(attr, lead_points, reported_votes)
            else:
                color = winner_take_all_color(attr, reported_votes)
            feature = feature_by_code.get(code)
            if feature is not None:
                fig.add_trace(_fixed_polygon_trace(feature, code, color, hover_by_code.get(code, "")))
    else:
        codes = [str(c) for c in rows.keys()]
        fig.add_trace(_neutral_base_trace(geojson, codes, [hover_by_code.get(c, "") for c in codes]))

        bubble_values = []
        bubble_codes = []
        bubble_lons = []
        bubble_lats = []
        bubble_text = []
        bubble_colors = []
        for code, row in rows.items():
            props = feature_props.get(code, {})
            lon = props.get("label_lon", props.get("label_x"))
            lat = props.get("label_lat", props.get("label_y"))
            if lon is None or lat is None:
                continue
            if mode == "リード票":
                value = _safe_float(row.get("lead_votes", 0), 0)
                if value <= 0:
                    continue
                attr = str(row.get("leader_attribute", ""))
                color = winner_take_all_color(attr, max(_safe_float(row.get("reported_votes", 0), 0), 1))
            else:
                value = _safe_float(row.get("remaining_votes", 0), 0)
                if value <= 0:
                    continue
                color = "#4A4A4A"
            bubble_values.append(value)
            bubble_codes.append(code)
            bubble_lons.append(float(lon))
            bubble_lats.append(float(lat))
            bubble_text.append(hover_by_code.get(code, ""))
            bubble_colors.append(color)

        if bubble_values:
            maxv = max(bubble_values)
            sizes = [8 + 38 * ((v / maxv) ** 0.5) for v in bubble_values]
            fig.add_trace(
                go.Scattermapbox(
                    lon=bubble_lons,
                    lat=bubble_lats,
                    mode="markers",
                    marker=dict(size=sizes, color=bubble_colors, opacity=0.72),
                    customdata=bubble_text,
                    hovertemplate="%{customdata}<extra></extra>",
                    name="",
                )
            )

    if show_labels:
        label_lon = []
        label_lat = []
        label_text = []
        for f in geojson["features"]:
            p = f["properties"]
            label_lon.append(float(p.get("label_lon", p.get("label_x", 0))))
            label_lat.append(float(p.get("label_lat", p.get("label_y", 0))))
            label_text.append(str(p.get("municipality_name", "")))
        fig.add_trace(
            go.Scattermapbox(
                lon=label_lon,
                lat=label_lat,
                mode="text",
                text=label_text,
                textfont=dict(size=10, color="#222222"),
                hoverinfo="skip",
                name="",
            )
        )

    preset = ZOOM_PRESETS.get(zoom_preset, ZOOM_PRESETS["全県"])
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=dict(
            style="carto-positron",
            center=preset["center"],
            zoom=preset["zoom"],
        ),
        showlegend=False,
        hovermode="closest",
        uirevision=f"real-map-{zoom_preset}",
        paper_bgcolor="white",
    )
    return fig
