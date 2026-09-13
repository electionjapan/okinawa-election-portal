
from pathlib import Path
from datetime import datetime, timedelta
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from live_data import GOOGLE_SHEET_ID, LiveSheetError, build_live_models, load_google_workbook

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

RED = "#C93238"
BLUE = "#1675B9"
RED_LIGHT = "#F4DBDD"
BLUE_LIGHT = "#DDEAF6"
GRAY = "#8E8E8E"
GRAY_LIGHT = "#EFEFEF"
TEXT = "#292929"
MUTED = "#6B6B6B"

ATTR_COLOR = {
    "保守系": RED,
    "オール沖縄系": BLUE,
    "革新系（2014年以前）": BLUE,
    "第三極・その他政党": "#8C8C8C",
    "独立・無所属": "#8C8C8C",
    "民主系": "#8C8C8C",
    "公明党": RED,
    "革新分裂候補": "#8C8C8C",
}

BLUE_BLOC_ATTRS = ["オール沖縄系", "革新系（2014年以前）"]

PLOT_CONFIG = {
    "scrollZoom": True,
    "doubleClick": "reset+autosize",
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines"],
}


# Portal navigation
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)
nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_live", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル / 開票速報</div>', unsafe_allow_html=True)
st.caption("v0.9.29 · LIVE SHEET · NEW MAP")

st.markdown(
    """
<style>
html, body, [class*="css"] { font-family: "Meiryo", "Yu Gothic", system-ui, sans-serif; color:#292929; }
.block-container { max-width: 1460px; padding-top: .6rem; padding-bottom: 4rem; }
.portal-nav-spacer { height: .15rem; }
.portal-breadcrumb {
  color:#777;
  font-size:.82rem;
  padding-top:.68rem;
  white-space:nowrap;
}
#MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stAppViewContainer"] { padding-top: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {
  position: sticky;
  top: 0;
  z-index: 999;
  background: #fff;
  padding-bottom: .3rem;
}
.nyt-title { font-family: Georgia, "Yu Mincho", serif; font-weight: 800; letter-spacing:-0.02em; line-height:1.05; }
.live-badge { display:inline-block; padding:3px 8px; border-radius:4px; color:white; background:#C93238; font-size:.75rem; font-weight:800; margin-right:8px; }
.demo-badge { display:inline-block; padding:3px 8px; border-radius:4px; color:#5a4700; background:#fff0a8; font-size:.75rem; font-weight:800; }
.live-source-badge { display:inline-block; padding:3px 8px; border-radius:4px; color:#164c2d; background:#daf4e3; font-size:.75rem; font-weight:800; }
.estimate-badge { display:inline-block; padding:2px 7px; border-radius:999px; color:#5a4700; background:#fff0a8; font-size:.72rem; font-weight:800; }
.refresh-line { color:#666; font-size:.84rem; margin:.25rem 0 .6rem; }
.status-chip { display:inline-block; padding:1px 7px; border-radius:999px; background:#efefef; font-size:.74rem; font-weight:700; }
.top-rule { border-top: 4px solid #111; margin: 8px 0 14px 0; }
.sub-rule { border-top: 1px solid #DADADA; margin: 12px 0 18px 0; }
.kicker { color:#6B6B6B; font-size:.94rem; }
.eyebrow { font-weight: 800; font-size: .85rem; letter-spacing: .08em; color: #555; text-transform: uppercase; }
.section-title { font-family: Georgia, "Yu Mincho", serif; font-size: 1.65rem; font-weight: 800; margin: 1.6rem 0 .1rem; }
.section-deck { color:#6B6B6B; font-size:.98rem; margin-bottom: .7rem; }
.winner-banner { padding: 18px 20px; color:white; border-radius:2px 2px 0 0; margin-top: .35rem; }
.winner-small { font-weight:800; font-size:.86rem; letter-spacing:.06em; }
.winner-main { font-family: Georgia, "Yu Mincho", serif; font-weight:800; font-size:1.7rem; margin-top:2px; }
.winner-margin { font-size:.92rem; font-weight:700; margin-top:6px; opacity:.95; }
.swing-line { font-size:1.02rem; padding:.15rem 0; }
.swing-result { border-top:1px dashed #ccc; margin-top:.4rem; padding-top:.5rem; font-size:1.1rem; }
.stat-strip { display:flex; flex-wrap:wrap; gap:16px; background:#f3f3f3; border-bottom:1px solid #ddd; padding:8px 13px; color:#666; font-size:.87rem; }
.stat-strip strong { color:#333; }
.result-card { border-top:1px solid #DADADA; padding: 11px 2px 10px 2px; }
.candidate-name { font-size:1.10rem; font-weight:700; }
.candidate-party { color:#6B6B6B; font-size:.85rem; }
.attr-badge {
  display:inline-block;
  color:#fff;
  font-size:.72rem;
  font-weight:700;
  padding:.14rem .62rem;
  border-radius:999px;
  margin-left:.45rem;
  vertical-align:middle;
  letter-spacing:.02em;
}
.big-num { font-size:1.22rem; font-weight:750; text-align:right; }
.pct-num { font-size:1.25rem; font-weight:800; text-align:right; }
.progress-outer { height:7px; width:100%; background:#eee; margin-top:7px; }
.progress-inner { height:7px; }
.guide-card { border:1px solid #ddd; border-radius:8px; padding:14px 16px; margin-bottom:12px; box-shadow:0 1px 2px rgba(0,0,0,.04); }
.guide-title { font-size:1.06rem; font-weight:800; border-bottom:3px solid #e4c51a; display:inline-block; padding-bottom:2px; margin-bottom:7px; }
.guide-metric { font-size:1.15rem; font-weight:800; margin:7px 0 3px; }
.guide-copy { color:#666; line-height:1.55; font-size:.9rem; }
.map-caption { font-size:.82rem; color:#666; margin-top:-5px; margin-bottom:4px; }
.note-box { background:#f7f7f7; border:1px solid #ddd; padding:10px 13px; font-size:.86rem; color:#666; border-radius:5px; }
.legend-row { display:flex; gap:18px; align-items:center; font-size:.82rem; color:#666; margin:.2rem 0 .5rem; }
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container,
.js-plotly-plot .nsewdrag, .js-plotly-plot svg {
  touch-action: none !important;
}
.js-plotly-plot .modebar { transform: scale(1.35); transform-origin: top right; }
.js-plotly-plot .modebar-btn { padding: 3px !important; }
@media (max-width: 800px) {
  .block-container {
    padding-left:.7rem;
    padding-right:.7rem;
    padding-top:.6rem !important;
  }
  .portal-nav-spacer { height:.15rem; }
  .portal-breadcrumb {
    padding-top:.35rem;
    font-size:.76rem;
    white-space:normal;
    line-height:1.35;
  }
  div[data-testid="stHorizontalBlock"]:first-of-type {
    gap:.35rem;
  }
  .winner-main { font-size:1.35rem; }
  .section-title { font-size:1.35rem; }
}
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_data
def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_all():
    results = pd.DataFrame(load_json("statewide_results.json"))
    elections = pd.DataFrame(load_json("elections.json"))
    turnout = pd.DataFrame(load_json("turnout.json"))
    municipalities = pd.DataFrame(load_json("municipalities.json"))
    geojson = load_json("map_layout_v0912.geojson")
    layout_boxes = load_json("map_layout_v0912.json")
    return results, elections, turnout, municipalities, geojson, layout_boxes

def serial_to_date(v):
    return datetime(1899, 12, 30) + timedelta(days=float(v))

def election_label(row):
    dt = serial_to_date(row["date_serial"])
    suffix = "知事選" if row["election_type"] == "知事選" else "参院選"
    return f"{dt.year} {suffix}"

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02X}" for v in rgb)

def blend(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))

def lead_fill_color(attribute, lead_points, reported_votes):
    if reported_votes <= 0:
        return GRAY_LIGHT
    if attribute == "同数" or abs(float(lead_points)) < 1e-12:
        return "#BDBDBD"
    t = min(abs(lead_points) / 25.0, 1.0)
    if attribute == "保守系":
        return blend(RED_LIGHT, RED, t)
    if attribute in BLUE_BLOC_ATTRS:
        return blend(BLUE_LIGHT, BLUE, t)
    return "#E3E3E3"

def candidate_color(attribute):
    return ATTR_COLOR.get(attribute, "#8C8C8C")

ATTR_BADGE_LABEL = {
    "保守系": "保守系",
    "オール沖縄系": "オール沖縄",
    "革新系（2014年以前）": "革新",
}

def attribute_badge(attribute):
    label = ATTR_BADGE_LABEL.get(attribute)
    if not label:
        return ""
    color = RED if attribute == "保守系" else BLUE
    return f'<span class="attr-badge" style="background:{color};">{label}</span>'

def compare_context_live(results, turnout, current, msum, compare_id):
    # current two-bloc margin
    dcur = current[current["attribute"].isin(["保守系", "オール沖縄系"])].copy()
    curr_margin = (
        dcur.groupby(["municipality_code", "attribute"], as_index=False)["current_votes"].sum()
        .pivot(index="municipality_code", columns="attribute", values="current_votes")
        .fillna(0).reset_index()
    )
    curr_total = current.groupby("municipality_code", as_index=False)["current_votes"].sum()
    for c in ["保守系", "オール沖縄系"]:
        if c not in curr_margin.columns:
            curr_margin[c] = 0.0
    curr_margin = curr_margin.merge(curr_total, on="municipality_code", how="left")
    curr_margin["current_margin"] = (
        100 * (curr_margin["保守系"] - curr_margin["オール沖縄系"]) / curr_margin["current_votes"].replace(0, pd.NA)
    ).fillna(0)

    dprev = results[results["election_id"] == compare_id].copy()
    top2 = []
    for code, grp in dprev.groupby("municipality_code"):
        grp = grp.sort_values("votes", ascending=False)
        top = grp.iloc[0]
        second = grp.iloc[1] if len(grp) > 1 else None
        vote_diff = float(top["votes"] - (second["votes"] if second is not None else 0))
        point_diff = 100 * vote_diff / float(top["valid_votes"]) if float(top["valid_votes"]) else 0
        top2.append({
            "municipality_code": code,
            "prev_winner_name": top["candidate_name"],
            "prev_winner_attribute": top["attribute"],
            "prev_vote_diff": vote_diff,
            "prev_point_diff": point_diff,
        })
    prev_summary = pd.DataFrame(top2)

    dprev2 = dprev.copy()
    dprev2["bloc"] = dprev2["attribute"].map(
        lambda x: "保守系" if x == "保守系" else ("青陣営" if x in BLUE_BLOC_ATTRS else None)
    )
    dprev2 = dprev2[dprev2["bloc"].notna()]
    prev_margin = (
        dprev2.groupby(["municipality_code", "bloc"], as_index=False)["votes"].sum()
        .pivot(index="municipality_code", columns="bloc", values="votes")
        .fillna(0).reset_index()
    )
    prev_valid = dprev.groupby("municipality_code", as_index=False)["valid_votes"].first()
    for c in ["保守系", "青陣営"]:
        if c not in prev_margin.columns:
            prev_margin[c] = 0.0
    prev_margin = prev_margin.merge(prev_valid, on="municipality_code", how="left")
    prev_margin["previous_margin"] = (
        100 * (prev_margin["保守系"] - prev_margin["青陣営"]) / prev_margin["valid_votes"].replace(0, pd.NA)
    ).fillna(0)

    swing = (
        msum[["municipality_code", "municipality_name", "reporting_pct"]]
        .merge(curr_margin[["municipality_code", "current_margin"]], on="municipality_code", how="left")
        .merge(prev_margin[["municipality_code", "previous_margin"]], on="municipality_code", how="left")
    )
    swing["shift"] = swing["current_margin"] - swing["previous_margin"]

    # Current turnout comes from the 2026 live sheet; comparison turnout comes from historical data.
    cur_turn = msum[["municipality_code", "turnout_rate"]].rename(columns={"turnout_rate": "current_turnout"})
    prev_turn = turnout[turnout["election_id"] == compare_id][["municipality_code", "turnout_rate"]].rename(columns={"turnout_rate": "previous_turnout"})
    turnout_comp = cur_turn.merge(prev_turn, on="municipality_code", how="left")
    turnout_comp["turnout_diff_pt"] = 100 * (pd.to_numeric(turnout_comp["current_turnout"], errors="coerce") - pd.to_numeric(turnout_comp["previous_turnout"], errors="coerce"))

    detail = (
        prev_summary
        .merge(turnout_comp, on="municipality_code", how="left")
        .merge(swing[["municipality_code", "current_margin", "previous_margin", "shift"]], on="municipality_code", how="left")
    )
    return detail, swing

def _geometry_xy(geometry):
    xs, ys = [], []
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polygons = [coords] if gtype == "Polygon" else coords if gtype == "MultiPolygon" else []
    for polygon in polygons:
        if not polygon:
            continue
        exterior = polygon[0]
        xs.extend([p[0] for p in exterior] + [None])
        ys.extend([p[1] for p in exterior] + [None])
    return xs, ys

def subset_geojson_many(geojson, groups):
    return {
        "type": "FeatureCollection",
        "features": [f for f in geojson["features"] if f["properties"].get("display_group") in groups],
    }

def _bounds_of_geojson(geojson):
    xs, ys = [], []
    for f in geojson["features"]:
        x, y = _geometry_xy(f["geometry"])
        xs.extend([v for v in x if v is not None])
        ys.extend([v for v in y if v is not None])
    return (min(xs), max(xs), min(ys), max(ys)) if xs else (0, 1, 0, 1)

def _finish_panel_map(fig, geojson, height=520, pad=0.025):
    minx, maxx, miny, maxy = _bounds_of_geojson(geojson)
    dx = max(maxx - minx, 1e-6)
    dy = max(maxy - miny, 1e-6)
    fig.update_xaxes(range=[minx - dx * pad, maxx + dx * pad], visible=False, fixedrange=False, constrain="domain")
    fig.update_yaxes(range=[miny - dy * pad, maxy + dy * pad], visible=False, fixedrange=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        dragmode="pan",
        hovermode="closest",
        showlegend=False,
        uirevision=True,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#C9C9C9",
            font=dict(family="Meiryo, Yu Gothic, sans-serif", size=13, color="#303030"),
            align="left",
            namelength=0,
        ),
    )
    return fig

def label_lookup(geojson):
    rows = []
    for f in geojson["features"]:
        p = f["properties"]
        rows.append({
            "municipality_code": str(p["municipality_code"]),
            "x": float(p.get("label_x", p.get("label_lon", 0))),
            "y": float(p.get("label_y", p.get("label_lat", 0))),
        })
    return pd.DataFrame(rows)

def winner_map_panel(geojson, msum, current, compare_detail, compare_label, height=520):
    m2 = msum.merge(compare_detail, on="municipality_code", how="left")
    by_code = {str(r["municipality_code"]): r for _, r in m2.iterrows()}
    current_groups = {str(code): grp.sort_values("current_votes", ascending=False) for code, grp in current.groupby("municipality_code")}
    fig = go.Figure()
    for feature in geojson["features"]:
        code = str(feature["properties"]["municipality_code"])
        r = by_code.get(code)
        if r is None:
            continue
        grp = current_groups.get(code)
        total = int(grp["current_votes"].sum()) if grp is not None else 0
        xs, ys = _geometry_xy(feature["geometry"])
        fill = lead_fill_color(r["leader_attribute"], r["lead_points"], total)

        prev_winner = r.get("prev_winner_name")
        prev_pt = r.get("prev_point_diff")
        if pd.isna(prev_winner) or not prev_winner:
            prev_line = ""
        elif prev_winner == "同数":
            prev_line = "（前回 同数）"
        elif pd.notna(prev_pt):
            prev_line = f"（前回 {prev_winner} +{prev_pt:.1f}pt差で勝利）"
        else:
            prev_line = f"（前回 {prev_winner} が勝利）"

        lines = []
        if grp is not None and total > 0:
            grp_rows = list(grp.iterrows())
            for i, (_, c) in enumerate(grp_rows):
                pct = 100 * c["current_votes"] / total
                lines.append(f"{c['candidate_name']}　{int(c['current_votes']):,}票　{pct:.1f}%")
                if i == 0 and len(grp_rows) > 1:
                    top_votes = float(c["current_votes"])
                    second_votes = float(grp_rows[1][1]["current_votes"])
                    if top_votes != second_votes:
                        margin_votes = int(top_votes - second_votes)
                        margin_pt = 100 * margin_votes / total
                        lines.append(
                            f"<span style='color:#8a8a8a;font-size:12px;'>（{margin_pt:.1f}ポイント　{margin_votes:,}票リード）</span>"
                        )
        else:
            lines.append("未開票")
        hover = (
            f"<b>{r['municipality_name']}</b>{prev_line}<br>"
            + "<br>".join(lines)
            + f"<br><br><b>開票率 {r['reporting_pct']:.1f}%</b>"
        )
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=fill,
            line=dict(color="white", width=1.1),
            text=hover, hovertemplate="%{text}<extra></extra>",
            hoveron="fills", showlegend=False, name="",
        ))
    return _finish_panel_map(fig, geojson, height=height)

def lead_bubble_panel(geojson, msum, height=420, max_value=1):
    loc = label_lookup(geojson)
    d = msum.merge(loc, on="municipality_code", how="inner")
    d["lead_display"] = d.apply(
        lambda r: "同数" if r.get("leader_attribute") == "同数"
        else f"{r['leader_name']}　+{int(r['lead_votes']):,}票",
        axis=1
    )
    fig = go.Figure()
    for feature in geojson["features"]:
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D4D4D4", width=0.7), hoverinfo="skip", showlegend=False, name=""))
    for attr, color in [("保守系", RED), ("革新・オール沖縄", BLUE), ("同数", "#8E8E8E"), ("その他", "#B8B8B8")]:
        if attr == "同数":
            sub = d[d["leader_attribute"] == "同数"]
        elif attr == "革新・オール沖縄":
            sub = d[d["leader_attribute"].isin(BLUE_BLOC_ATTRS)]
        elif attr == "その他":
            sub = d[~d["leader_attribute"].isin(["保守系", *BLUE_BLOC_ATTRS, "同数"])]
        else:
            sub = d[d["leader_attribute"] == attr]
        sub = sub[pd.to_numeric(sub["reported_votes"], errors="coerce").fillna(0) > 0]
        if sub.empty:
            continue
        sizes = 8 + 42 * (sub["lead_votes"].astype(float) / max(max_value, 1)).pow(0.5)
        detail = (
            "<b>" + sub["municipality_name"] + "</b><br>"
            + sub["leader_name"] + " +" + sub["lead_votes"].map(lambda x: f"{x:,.0f}") + "票<br>"
            + "リード差 " + sub["lead_points"].map(lambda x: f"{x:.1f}pt") + "<br>"
            + "開票率 " + sub["reporting_pct"].map(lambda x: f"{x:.1f}%")
        )
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers",
            marker=dict(size=sizes, color=color, opacity=0.35, line=dict(color=color, width=1.4)),
            text=detail, hovertemplate="%{text}<extra></extra>", showlegend=False, name="",
        ))
    return _finish_panel_map(fig, geojson, height=height)

def _fmt_turnout(v):
    return "―" if pd.isna(v) else f"{100*float(v):.1f}%"

def _fmt_diff_pt(v):
    if pd.isna(v):
        return "―"
    sign = "+" if float(v) > 0 else ""
    return f"{sign}{float(v):.1f}pt"

def remaining_bubble_panel(geojson, msum, compare_detail, compare_label, height=420, max_value=1):
    loc = label_lookup(geojson)
    d = msum.merge(loc, on="municipality_code", how="inner").merge(compare_detail, on="municipality_code", how="left")
    fig = go.Figure()
    for feature in geojson["features"]:
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D4D4D4", width=0.7), hoverinfo="skip", showlegend=False, name=""))
    for attr, color in [("保守系", RED), ("革新・オール沖縄", BLUE), ("同数", "#8E8E8E"), ("その他", "#B8B8B8")]:
        if attr == "同数":
            sub = d[d["leader_attribute"] == "同数"]
        elif attr == "革新・オール沖縄":
            sub = d[d["leader_attribute"].isin(BLUE_BLOC_ATTRS)]
        elif attr == "その他":
            sub = d[~d["leader_attribute"].isin(["保守系", *BLUE_BLOC_ATTRS, "同数"])]
        else:
            sub = d[d["leader_attribute"] == attr]
        sub = sub[pd.to_numeric(sub["remaining_votes"], errors="coerce") > 0]
        if sub.empty:
            continue
        sizes = 8 + 42 * (sub["remaining_votes"].astype(float) / max(max_value, 1)).pow(0.5)
        detail = (
            "<b style='font-size:16px'>" + sub["municipality_name"] + "</b><br>"
            + "<span style='font-size:15px'><b>残票 " + sub["remaining_votes"].map(lambda x: f"{x:,.0f}") + "票</b></span><br>"
            + "<span style='font-size:14px'>開票率 " + sub["reporting_pct"].map(lambda x: f"{x:.1f}%")
            + "　/　開票済み " + sub["reported_votes"].map(lambda x: f"{x:,.0f}") + "票"
            + "　/　投票者数 " + sub["voters_total"].map(lambda x: "―" if pd.isna(x) else f"{x:,.0f}") + "人</span><br><br>"
            + "<span style='font-size:13px'>今回投票率 " + sub["current_turnout"].map(_fmt_turnout)
            + "　（前回選比 " + sub["turnout_diff_pt"].map(_fmt_diff_pt) + "）</span><br>"
            + "<span style='font-size:13px'>" + compare_label + "："
            + sub["prev_winner_name"].fillna("―") + " が "
            + sub["prev_point_diff"].map(lambda x: f"{x:.1f}pt" if pd.notna(x) else "―")
            + "・" + sub["prev_vote_diff"].map(lambda x: f"{x:,.0f}票差" if pd.notna(x) else "―")
            + " で勝利</span>"
        )
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers",
            marker=dict(size=sizes, color=color, opacity=0.28, line=dict(color=color, width=1.4)),
            text=detail, hovertemplate="%{text}<extra></extra>", showlegend=False, name="",
        ))
    return _finish_panel_map(fig, geojson, height=height)

def shift_map_panel(geojson, swing, threshold, global_max_shift, height=420):
    codes = {str(f["properties"]["municipality_code"]) for f in geojson["features"]}
    loc = label_lookup(geojson)
    s = swing[(swing["municipality_code"].isin(codes)) & (swing["reporting_pct"] >= threshold)].copy().merge(loc, on="municipality_code", how="left")
    fig = go.Figure()
    for feature in geojson["features"]:
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D7D7D7", width=0.75), hoverinfo="skip", showlegend=False, name=""))
    max_abs = max(float(global_max_shift), 1.0)

    for direction, color, symbol, positive in [
        ("保守", RED, "triangle-right", True),
        ("革新・オール沖縄", BLUE, "triangle-left", False),
    ]:
        line_x, line_y = [], []
        mark_x, mark_y, mark_size, mark_text = [], [], [], []
        part = s[s["shift"] > 0] if positive else s[s["shift"] < 0]
        for _, r in part.iterrows():
            shift = abs(float(r["shift"]))
            if shift < 0.15:
                continue
            x = float(r["x"]); y = float(r["y"])
            length = 0.8 + 6.2 * min(shift / max_abs, 1)
            if positive:
                tail, head = x - length, x + length * 0.2
            else:
                tail, head = x + length, x - length * 0.2
            line_x += [tail, head, None]
            line_y += [y, y, None]
            mark_x.append(head); mark_y.append(y)
            mark_size.append(7 + 10 * min(shift / max_abs, 1))
            mark_text.append(f"<b>{r['municipality_name']}</b><br>{direction}方向へ {shift:.1f}pt<br>開票率 {r['reporting_pct']:.1f}%")
        if line_x:
            fig.add_trace(go.Scatter(x=line_x, y=line_y, mode="lines", line=dict(color=color, width=2.0), hoverinfo="skip", showlegend=False, name=""))
            fig.add_trace(go.Scatter(
                x=mark_x, y=mark_y, mode="markers",
                marker=dict(symbol=symbol, size=mark_size, color=color, line=dict(color=color, width=1.0)),
                text=mark_text, hovertemplate="%{text}<extra></extra>", showlegend=False, name="",
            ))
    return _finish_panel_map(fig, geojson, height=height)

def add_layout_boxes(fig, layout_boxes):
    boxes = layout_boxes.get("boxes", {})
    labels = layout_boxes.get("labels", {})
    for key, box in boxes.items():
        if key == "本島":
            continue
        x0, y0, x1, y1 = [float(v) for v in box]
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color="#D8D8D8", width=1.0),
            fillcolor="rgba(255,255,255,0)",
            layer="below",
        )
        label = labels.get(key)
        if label:
            fig.add_annotation(
                x=x0 + 1.0, y=y1 - 0.9,
                text=f"<b>{label}</b>", showarrow=False,
                xanchor="left", yanchor="top",
                font=dict(size=12, color="#666666", family="Meiryo, Yu Gothic, sans-serif"),
                bgcolor="rgba(255,255,255,0.88)", borderpad=2,
            )
    return fig

def apply_zoom(fig, zoom):
    if zoom and zoom != 1.0:
        xr = list(fig.layout.xaxis.range) if fig.layout.xaxis.range else None
        yr = list(fig.layout.yaxis.range) if fig.layout.yaxis.range else None
        if xr and yr:
            cx, cy = (xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2
            hx, hy = (xr[1] - xr[0]) / 2 / zoom, (yr[1] - yr[0]) / 2 / zoom
            fig.update_xaxes(range=[cx - hx, cx + hx])
            fig.update_yaxes(range=[cy - hy, cy + hy])
    return fig

def render_boxed_map(panel_fn, geojson, layout_boxes, height, key_prefix, *args, **kwargs):
    zoom_pct = st.slider("拡大", 100, 400, 100, step=20, key=f"{key_prefix}-zoom", format="%d%%")
    fig = panel_fn(geojson, *args, height=height, **kwargs)
    fig = add_layout_boxes(fig, layout_boxes)
    fig = apply_zoom(fig, zoom_pct / 100.0)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=PLOT_CONFIG,
        key=f"{key_prefix}-boxed",
    )

def render_candidate_totals(totals, previous_totals=None):
    """候補者カードをMarkdownに誤解釈されない連続HTMLとして生成する。"""
    html = []
    prev = previous_totals or {}
    for _, r in totals.iterrows():
        color = candidate_color(r["attribute"])
        meta = " / ".join([x for x in [str(r.get("incumbency") or ""), str(r.get("party") or "")] if x])
        endorsement = str(r.get("endorsement") or "").strip()
        published = bool(r.get("has_published", True))
        delta = int(r["current_votes"]) - int(prev.get(r["candidate_name"], int(r["current_votes"]))) if published else 0
        delta_html = f'<span style="color:#777;font-size:.78rem;">前回更新から +{delta:,}</span>' if delta > 0 else ''
        vote_text = f"{int(r['current_votes']):,}" if published else "―"
        pct_text = f"{float(r['pct']):.2f}%" if published else "―"
        endorsement_html = f'<br><span class="candidate-party">{endorsement}</span>' if endorsement else ''

        # Streamlit の st.markdown は、空行の後にインデントされた HTML が来ると
        # Markdown のコードブロックとして扱うことがある。推薦・支援が空欄でも
        # HTML ブロックを分断しないよう、カード全体を改行なしで連結する。
        html.append(
            f'<div class="result-card" style="border-left:7px solid {color}; padding-left:12px;">'
            f'<div style="display:grid;grid-template-columns:1.6fr .8fr .65fr;gap:10px;align-items:end;">'
            f'<div><span class="candidate-name">{r["candidate_name"]}</span>{attribute_badge(r["attribute"])}<br>'
            f'<span class="candidate-party">{meta}</span>{endorsement_html}</div>'
            f'<div class="big-num">{vote_text}<br>{delta_html}</div>'
            f'<div class="pct-num">{pct_text}</div>'
            f'</div>'
            f'<div class="progress-outer"><div class="progress-inner" style="width:{min(float(r["pct"]),100):.2f}%;background:{color};"></div></div>'
            f'</div>'
        )
    return "".join(html)

def statewide_margin_current(current):
    t = current[current["attribute"].isin(["保守系", "オール沖縄系"])].groupby("attribute")["current_votes"].sum()
    all_votes = current["current_votes"].sum()
    return 0.0 if all_votes == 0 else 100 * (t.get("保守系", 0) - t.get("オール沖縄系", 0)) / all_votes

def statewide_margin_final(results, election_id):
    d = results[results["election_id"] == election_id]
    cons = d.loc[d["attribute"] == "保守系", "votes"].sum()
    blue = d.loc[d["attribute"].isin(BLUE_BLOC_ATTRS), "votes"].sum()
    all_votes = d["votes"].sum()
    return 0.0 if all_votes == 0 else 100 * (cons - blue) / all_votes

def camp_candidate_names(df, name_col="candidate_name", attr_col="attribute"):
    """保守系候補・オール沖縄系候補それぞれの名前を返す（無ければ空文字）。"""
    cons_rows = df[df[attr_col] == "保守系"]
    blue_rows = df[df[attr_col].isin(BLUE_BLOC_ATTRS)]
    cons_name = cons_rows[name_col].iloc[0] if not cons_rows.empty else ""
    blue_name = blue_rows[name_col].iloc[0] if not blue_rows.empty else ""
    return cons_name, blue_name

# -------------------- data --------------------
results, elections, turnout, municipalities, geojson, layout_boxes = load_all()

# Automatic refresh interval (seconds). Kept short per user request, balanced against
# not hammering the public Google Sheet.
LIVE_REFRESH_SEC = 15
if st_autorefresh is not None:
    st_autorefresh(interval=LIVE_REFRESH_SEC * 1000, limit=None, key="live-sheet-autorefresh")

with st.sidebar:
    st.markdown("### 開票速報")
    if st.button("↻ 最新の状態を再取得", key="refresh_live_sheet", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    current_meta = elections[elections["election_id"] == "GOV2022"].iloc[0]
    prior = elections.copy().sort_values("date_serial", ascending=False)
    prior["label"] = prior.apply(election_label, axis=1)
    compare_options = prior[["label", "election_id"]]
    default_idx = compare_options["election_id"].tolist().index("GOV2022") if "GOV2022" in compare_options["election_id"].tolist() else 0
    default_compare_label = compare_options["label"].tolist()[default_idx]
    # 実際の選択ウィジェットは下部の「過去の選挙からどちらへ動いたか」の直前に置く。
    # ここではまだそのウィジェットが描画されていないので、前回の選択値を
    # session_stateから読み、無ければ既定値（2022年知事選）を使う。
    compare_label = st.session_state.get("compare_election_select", default_compare_label)
    if compare_label not in compare_options["label"].tolist():
        compare_label = default_compare_label
    compare_id = compare_options.loc[compare_options["label"] == compare_label, "election_id"].iloc[0]

    swing_threshold = st.select_slider("シフト表示の最低開票率", options=[25, 50, 75, 90, 95, 100], value=50)
    sort_mode = st.selectbox("市町村一覧の並べ替え", ["得票規模", "開票率", "リード票", "接戦順", "残票", "県の並び順"])
    st.caption("手動更新ボタンでも即時に最新の状態を取得できます。")
    st.caption("地図は本島を中央、周辺離島を外周インセットへ再配置した模式図です。")

@st.cache_data(ttl=12, show_spinner=False)
def get_live_book(sheet_id):
    return load_google_workbook(sheet_id)

try:
    live_book = get_live_book(GOOGLE_SHEET_ID)
    st.session_state["live_last_good_book"] = live_book
    st.session_state["live_last_error"] = ""
except Exception as exc:
    st.session_state["live_last_error"] = str(exc)
    live_book = st.session_state.get("live_last_good_book")

if live_book is None:
    st.error("開票速報データを取得できません。データ元の共有設定を確認したうえで再取得してください。")
    if st.session_state.get("live_last_error"):
        st.caption(f"取得エラー: {st.session_state['live_last_error']}")
    st.stop()

try:
    invalid_history = pd.DataFrame(load_json("invalid_history_v1.json"))
except FileNotFoundError:
    invalid_history = pd.DataFrame(columns=["municipality_name", "rate_weighted", "rate_min", "rate_max"])

try:
    models = build_live_models(live_book, municipalities, invalid_history=invalid_history)
except Exception as exc:
    st.error(f"データの列構成を読み取れませんでした: {exc}")
    st.stop()

current = models.current
msum = models.msum
totals = models.totals
overall_reporting = models.overall_reporting
compare_detail, swing = compare_context_live(results, turnout, current, msum, compare_id)
state_shift = statewide_margin_current(current) - statewide_margin_final(results, compare_id)
global_max_shift = max(float(swing["shift"].abs().max()) if not swing.empty else 1.0, 1.0)

# Candidate deltas are session-local: enough to show changes between automatic refreshes without
# requiring a history sheet or writing anything back to Google Sheets.
prev_totals = st.session_state.get("live_previous_candidate_totals", {})
current_total_map = {r["candidate_name"]: int(r["current_votes"]) for _, r in totals.iterrows()}

# -------------------- page --------------------
st.markdown('<span class="live-badge">開票速報</span><span class="live-source-badge">LIVE</span>', unsafe_allow_html=True)
st.markdown('<div class="nyt-title" style="font-size:2.25rem;margin-top:8px;">2026 沖縄県知事選 開票速報</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="kicker">2026年9月13日投開票。</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)

ranked_totals = totals.sort_values(["current_votes", "candidate_id"], ascending=[False, True])
leader = ranked_totals.iloc[0] if not ranked_totals.empty and ranked_totals["current_votes"].sum() else None
runner_up = ranked_totals.iloc[1] if len(ranked_totals) > 1 and leader is not None else None
state_tie = (
    len(ranked_totals) >= 2 and int(ranked_totals.iloc[0]["current_votes"]) == int(ranked_totals.iloc[1]["current_votes"])
) if leader is not None else False
leader_color = "#8E8E8E" if state_tie else (candidate_color(leader["attribute"]) if leader is not None else "#808080")
leader_name = "同数" if state_tie else (leader["candidate_name"] if leader is not None else "未開票")
banner_label = "現在のリード" if overall_reporting is None or overall_reporting < 99.95 else "確定結果"
reporting_text = "―" if overall_reporting is None else f"{overall_reporting:.1f}%"
all_voters_known = bool(len(msum)) and bool(msum["voters_total"].notna().all())
remaining_total = pd.to_numeric(msum["remaining_votes"], errors="coerce").sum(min_count=1) if all_voters_known else pd.NA
remaining_text = "―" if pd.isna(remaining_total) else f"{int(round(float(remaining_total))):,}票"
counted_total = pd.to_numeric(msum["reported_votes"], errors="coerce").sum(min_count=1)
counted_text = "―" if pd.isna(counted_total) else f"{int(round(float(counted_total))):,}票"

if leader is not None and runner_up is not None and not state_tie:
    margin_votes_top = int(leader["current_votes"]) - int(runner_up["current_votes"])
    total_top_votes = float(ranked_totals["current_votes"].sum())
    margin_pt_top = (100 * margin_votes_top / total_top_votes) if total_top_votes > 0 else 0.0
    margin_html = f'<div class="winner-margin">次点（{runner_up["candidate_name"]}）比 +{margin_pt_top:.1f}pt（+{margin_votes_top:,}票）</div>'
elif state_tie:
    margin_html = '<div class="winner-margin">次点と同数です</div>'
else:
    margin_html = ""

invalid_range = "未算出"
if models.invalid_low is not None and models.invalid_high is not None:
    invalid_range = f"約{int(round(models.invalid_low)):,}～{int(round(models.invalid_high)):,}票"
    if models.invalid_center is not None:
        invalid_range += f"（中心 {int(round(models.invalid_center)):,}票）"

st.markdown(
    f"""
<div class="winner-banner" style="background:{leader_color};">
  <div class="winner-small">{banner_label}</div>
  <div class="winner-main">{leader_name}</div>
  {margin_html}
</div>
<div class="stat-strip">
  <span>全県開票率 <strong>{reporting_text}</strong></span>
  <span>開票済み <strong>{counted_text}</strong></span>
  <span>残票 <strong>{remaining_text}</strong></span>
  <span>確定自治体 <strong>{models.confirmed_count} / 41</strong></span>
  <span><span class="estimate-badge">独自推計</span> 無効票 <strong>{invalid_range}</strong></span>
</div>
""",
    unsafe_allow_html=True,
)
if st.session_state.get("live_last_error"):
    st.warning("直近のデータ取得に失敗したため、最後に正常取得できたデータを表示しています。")

left, right = st.columns([1.05, 1.15], gap="large")
with left:
    st.markdown('<div class="eyebrow">全県集計</div>', unsafe_allow_html=True)
    st.markdown(render_candidate_totals(totals, prev_totals), unsafe_allow_html=True)
    st.caption("開票途中の％は『開票済み候補者票の構成比』です。最終確定後の正式な得票率とは区別しています。")

with right:
    st.markdown('<div class="eyebrow">市町村別マップ</div>', unsafe_allow_html=True)
    map_mode = st.radio("表示切替", ["得票シェア", "リード票", "残票"], horizontal=True, label_visibility="collapsed")
    lead_max = float(msum["lead_votes"].max()) if len(msum) else 1
    remain_max = float(pd.to_numeric(msum["remaining_votes"], errors="coerce").max()) if pd.to_numeric(msum["remaining_votes"], errors="coerce").notna().any() else 1
    if map_mode == "得票シェア":
        render_boxed_map(winner_map_panel, geojson, layout_boxes, 610, "winner", msum, current, compare_detail, compare_label)
        st.markdown('<div class="map-caption">濃い赤・濃い青ほどリード幅が大きく、淡い色ほど接戦。未開票はグレーです。</div>', unsafe_allow_html=True)
    elif map_mode == "リード票":
        render_boxed_map(lead_bubble_panel, geojson, layout_boxes, 520, "lead", msum, max_value=lead_max)
        st.markdown('<div class="map-caption">円の大きさ＝現時点の1位と2位の票差。</div>', unsafe_allow_html=True)
    else:
        render_boxed_map(remaining_bubble_panel, geojson, layout_boxes, 520, "remain", msum, compare_detail, compare_label, max_value=remain_max)
        st.markdown('<div class="map-caption">円の大きさ＝公式系の残票。推計無効票は残票の内数であり、残票から勝手に差し引いていません。</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">41市町村の開票状況</div>', unsafe_allow_html=True)
st.markdown('<div class="section-deck">6候補の得票、開票率、残票、推計無効票を同じ表で追います。公式値と独自推計を分けて表示します。</div>', unsafe_allow_html=True)

tbl = msum.copy()
tbl["リード"] = tbl.apply(lambda r: "未開票" if float(r["reported_votes"] or 0) == 0 else f"{r['leader_name']} +{r['lead_points']:.1f}pt", axis=1)
tbl["リード票"] = tbl["lead_votes"].fillna(0).astype(int)
tbl["開票率"] = pd.to_numeric(tbl["reporting_pct"], errors="coerce").where(tbl["reporting_available"], pd.NA)
tbl["開票済み票"] = pd.to_numeric(tbl["reported_votes"], errors="coerce")
tbl["残票"] = pd.to_numeric(tbl["remaining_votes"], errors="coerce")
tbl["推計無効票"] = tbl.apply(
    lambda r: (
        "―" if r["status"] == "確定"
        else (
            f"約{int(r['invalid_low']):,}～{int(r['invalid_high']):,}票"
            if pd.notna(r["invalid_low"]) and pd.notna(r["invalid_high"]) else "―"
        )
    ), axis=1
)
tbl["状態"] = tbl["status"]
tbl["接戦度"] = tbl["lead_points"].abs()
tbl = tbl.merge(swing[["municipality_code", "current_margin"]], on="municipality_code", how="left")

# Candidate vote columns: official inputs from the live sheet, filing order from 00_候補者.
wide_votes = current.pivot(index="municipality_code", columns="candidate_name", values="display_votes").reset_index()
tbl = tbl.merge(wide_votes, on="municipality_code", how="left")

if sort_mode == "得票規模":
    tbl = tbl.sort_values("voters_total", ascending=False, na_position="last")
elif sort_mode == "開票率":
    tbl = tbl.sort_values("開票率", ascending=False, na_position="last")
elif sort_mode == "リード票":
    tbl = tbl.sort_values("current_margin", ascending=True, na_position="last")
elif sort_mode == "接戦順":
    tbl = tbl[tbl["reported_votes"] > 0].sort_values("接戦度", ascending=True)
elif sort_mode == "残票":
    tbl = tbl.sort_values("残票", ascending=False, na_position="last")
else:
    tbl = tbl.merge(municipalities[["municipality_code", "sort_no"]], on="municipality_code", how="left").sort_values("sort_no")

candidate_names = [r["candidate_name"] for _, r in models.candidates.sort_values("candidate_id").iterrows()]
show_cols = ["municipality_name", "状態", "開票率"] + candidate_names + ["残票", "推計無効票"]
table_show = tbl[show_cols].rename(columns={"municipality_name": "市町村"})

st.dataframe(
    table_show, hide_index=True, use_container_width=True, height=650,
    column_config={
        "開票率": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        **{name: st.column_config.NumberColumn(format="%d") for name in candidate_names},
        "残票": st.column_config.NumberColumn(format="%d"),
    },
)

with st.expander("市町村の詳細を見る", expanded=False):
    options = tbl["municipality_name"].tolist()
    selected = st.selectbox("市町村", options, key="live_muni_detail")
    r = tbl[tbl["municipality_name"] == selected].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("投票者数", "―" if pd.isna(r["voters_total"]) else f"{int(r['voters_total']):,}人")
    c2.metric("投票率", "―" if pd.isna(r["turnout_rate"]) else f"{100*float(r['turnout_rate']):.1f}%")
    c3.metric("開票率", "―" if pd.isna(r["開票率"]) else f"{float(r['開票率']):.1f}%")
    c4.metric("残票", "―" if pd.isna(r["残票"]) else f"{int(r['残票']):,}票")
    is_final = r["status"] == "確定"
    d1, d2, d3 = st.columns(3)
    d1.metric("推計無効票・下限", "―" if is_final or pd.isna(r["invalid_low"]) else f"約{int(r['invalid_low']):,}票")
    d2.metric("推計無効票・中心", "―" if is_final or pd.isna(r["invalid_center"]) else f"約{int(r['invalid_center']):,}票")
    d3.metric("推計無効票・上限", "―" if is_final or pd.isna(r["invalid_high"]) else f"約{int(r['invalid_high']):,}票")
    if not is_final and (pd.notna(r["valid_remaining_low"]) or pd.notna(r["valid_remaining_high"])):
        st.caption(
            "推計有効残票："
            + ("―" if pd.isna(r["valid_remaining_low"]) else f"約{int(r['valid_remaining_low']):,}")
            + "～"
            + ("―" if pd.isna(r["valid_remaining_high"]) else f"{int(r['valid_remaining_high']):,}票")
        )
    selected_votes = current[current["municipality_name"] == selected].sort_values("candidate_id")
    st.dataframe(
        selected_votes[["candidate_name", "current_votes"]].rename(columns={"candidate_name": "候補者", "current_votes": "得票"}),
        hide_index=True, use_container_width=True,
        column_config={"得票": st.column_config.NumberColumn(format="%d")},
    )

st.markdown('<div class="section-title">過去の選挙からどちらへ動いたか</div>', unsafe_allow_html=True)
compare_label = st.selectbox(
    "比較する過去の選挙",
    compare_options["label"].tolist(),
    index=compare_options["label"].tolist().index(compare_label),
    key="compare_election_select",
)
compare_id = compare_options.loc[compare_options["label"] == compare_label, "election_id"].iloc[0]
if current["current_votes"].sum() > 0:
    past_margin = statewide_margin_final(results, compare_id)
    current_margin = statewide_margin_current(current)
    # state_shift = current_margin - past_margin （A:過去 → B:今回 → C:スイング）
    past_cons_name, past_blue_name = camp_candidate_names(results[results["election_id"] == compare_id], name_col="candidate_name")
    cur_cons_name, cur_blue_name = camp_candidate_names(current)
    past_winner_name = past_cons_name if past_margin >= 0 else past_blue_name
    current_leader_name = cur_cons_name if current_margin >= 0 else cur_blue_name
    direction = "保守" if state_shift > 0 else "オール沖縄"
    direction_color = RED if state_shift > 0 else BLUE
    current_verb = "リード" if (overall_reporting is None or overall_reporting < 99.95) else "勝利"

    st.markdown(
        f"""
<div class="section-deck">
  <div class="swing-line">{compare_label}　<strong>{past_winner_name}</strong> +{abs(past_margin):.1f}pt差で勝利</div>
  <div class="swing-line">今回の知事選　<strong>{current_leader_name}</strong> +{abs(current_margin):.1f}pt差で{current_verb}</div>
  <div class="swing-line swing-result">スイング　<span style="color:{direction_color};font-weight:800;">{direction}へ +{abs(state_shift):.1f}pt</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(f"地図は開票率 {swing_threshold}% 以上の市町村のみ表示します。比較する過去選挙はサイドバーから変更できます。")
    s_left, s_right = st.columns([1.1, 1.0], gap="large")
    with s_left:
        render_boxed_map(shift_map_panel, geojson, layout_boxes, 510, "shift", swing, swing_threshold, global_max_shift)
        st.markdown(
            f'<div class="legend-row"><span style="color:{RED};font-weight:800;">→ 保守方向</span><span style="color:{BLUE};font-weight:800;">← 革新・オール沖縄方向</span></div>',
            unsafe_allow_html=True,
        )
    with s_right:
        comp = swing[swing["reporting_pct"] >= swing_threshold].copy()
        comp["今回マージン"] = comp["current_margin"].map(lambda x: f"保守 +{x:.1f}" if x >= 0 else f"オール沖縄 +{abs(x):.1f}")
        comp["比較選挙マージン"] = comp["previous_margin"].map(lambda x: f"保守 +{x:.1f}" if x >= 0 else f"オール沖縄 +{abs(x):.1f}")
        comp["シフト"] = comp["shift"].map(lambda x: f"保守へ +{x:.1f}" if x >= 0 else f"オール沖縄へ +{abs(x):.1f}")
        comp["開票率"] = comp["reporting_pct"]
        comp = comp.sort_values("shift", key=lambda x: x.abs(), ascending=False)
        st.dataframe(
            comp[["municipality_name", "今回マージン", "比較選挙マージン", "シフト", "開票率"]].rename(columns={"municipality_name": "市町村"}),
            hide_index=True, use_container_width=True, height=560,
            column_config={"開票率": st.column_config.NumberColumn(format="%.1f%%")},
        )
else:
    st.info("候補者得票が入り始めると、過去の知事選・参院選との保革シフトを表示します。")

st.markdown('<div class="sub-rule"></div>', unsafe_allow_html=True)
st.caption(
    "v0.9.29｜公式値：投票者数・投票率・候補者得票・開票率・無効票確定・残票。"
    "独自推計：推計無効票・推計有効残票・補正係数。推計値には『推計』『約』を付けています。"
)

# Save only after the page has rendered, so the next rerun can show per-candidate increases.
st.session_state["live_previous_candidate_totals"] = current_total_map
