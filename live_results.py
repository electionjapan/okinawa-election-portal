
from pathlib import Path
from datetime import datetime, timedelta
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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

CURRENT_ELECTION = "GOV2022"

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
st.caption("v0.9.20 · NEW MAP · 模式配置")

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
.top-rule { border-top: 4px solid #111; margin: 8px 0 14px 0; }
.sub-rule { border-top: 1px solid #DADADA; margin: 12px 0 18px 0; }
.kicker { color:#6B6B6B; font-size:.94rem; }
.eyebrow { font-weight: 800; font-size: .85rem; letter-spacing: .08em; color: #555; text-transform: uppercase; }
.section-title { font-family: Georgia, "Yu Mincho", serif; font-size: 1.65rem; font-weight: 800; margin: 1.6rem 0 .1rem; }
.section-deck { color:#6B6B6B; font-size:.98rem; margin-bottom: .7rem; }
.winner-banner { padding: 18px 20px; color:white; border-radius:2px 2px 0 0; margin-top: .35rem; }
.winner-small { font-weight:800; font-size:.86rem; letter-spacing:.06em; }
.winner-main { font-family: Georgia, "Yu Mincho", serif; font-weight:800; font-size:1.7rem; margin-top:2px; }
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

def stable_seed(text):
    return sum((i + 1) * ord(c) for i, c in enumerate(str(text)))

def local_progress(global_pct, municipality_code):
    if global_pct >= 100:
        return 1.0
    start = 3 + (stable_seed(municipality_code) % 29)
    return max(0.0, min(1.0, (global_pct - start) / (100 - start)))

def candidate_curve(local_p, municipality_code, candidate_id):
    if local_p <= 0:
        return 0.0
    if local_p >= 1:
        return 1.0
    seed = stable_seed(f"{municipality_code}-{candidate_id}")
    exponent = 0.82 + (seed % 37) / 100.0
    return min(1.0, local_p ** exponent)

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

def build_final_results(results, election_id):
    d = results[results["election_id"] == election_id].copy()
    valid = (
        d.groupby(["municipality_code", "municipality_name"], as_index=False)["valid_votes"]
        .first().rename(columns={"valid_votes": "final_valid_votes"})
    )
    return d, valid

def simulate_snapshot(results, municipalities, global_pct):
    final, valid = build_final_results(results, CURRENT_ELECTION)
    rows = []
    for _, r in final.iterrows():
        lp = local_progress(global_pct, r["municipality_code"])
        factor = candidate_curve(lp, r["municipality_code"], r["candidate_id"])
        rows.append({**r.to_dict(), "current_votes": int(round(float(r["votes"]) * factor))})
    current = pd.DataFrame(rows)

    msum = (
        current.groupby(["municipality_code", "municipality_name"], as_index=False)["current_votes"]
        .sum().rename(columns={"current_votes": "reported_votes"})
        .merge(valid, on=["municipality_code", "municipality_name"], how="left")
        .merge(municipalities, on=["municipality_code", "municipality_name"], how="left")
    )
    msum["reporting_pct"] = (
        100 * msum["reported_votes"] / msum["final_valid_votes"].replace(0, pd.NA)
    ).fillna(0).clip(0, 100)
    msum["remaining_votes"] = (msum["final_valid_votes"] - msum["reported_votes"]).clip(lower=0)

    leader_rows = []
    for code, grp in current.groupby("municipality_code"):
        grp = grp.sort_values("current_votes", ascending=False)
        total = int(grp["current_votes"].sum())
        top = grp.iloc[0]
        second = grp.iloc[1] if len(grp) > 1 else None
        top_votes = int(top["current_votes"]) if total else 0
        second_votes = int(second["current_votes"]) if (total and second is not None) else 0
        is_tie = total > 0 and second is not None and top_votes == second_votes
        lead_votes = 0 if is_tie else (top_votes - second_votes if total else 0)
        lead_points = 100 * lead_votes / total if total else 0.0
        leader_rows.append({
            "municipality_code": code,
            "leader_name": "同数" if is_tie else (top["candidate_name"] if total else "未開票"),
            "leader_attribute": "同数" if is_tie else (top["attribute"] if total else ""),
            "lead_votes": lead_votes,
            "lead_points": lead_points,
            "is_tie": is_tie,
        })
    msum = msum.merge(pd.DataFrame(leader_rows), on="municipality_code", how="left")

    totals = (
        current.groupby(["candidate_id", "candidate_name", "party", "attribute", "result"], as_index=False)["current_votes"]
        .sum().sort_values("current_votes", ascending=False)
    )
    total_reported = totals["current_votes"].sum()
    totals["pct"] = 100 * totals["current_votes"] / total_reported if total_reported else 0.0
    overall_reporting = 100 * msum["reported_votes"].sum() / msum["final_valid_votes"].sum()
    return current, msum, totals, overall_reporting

def compare_context(results, turnout, current, msum, compare_id):
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

    # turnout comparison (available only where data exists)
    cur_turn = turnout[turnout["election_id"] == CURRENT_ELECTION][["municipality_code", "turnout_rate"]].rename(columns={"turnout_rate": "current_turnout"})
    prev_turn = turnout[turnout["election_id"] == compare_id][["municipality_code", "turnout_rate"]].rename(columns={"turnout_rate": "previous_turnout"})
    turnout_comp = cur_turn.merge(prev_turn, on="municipality_code", how="left")
    turnout_comp["turnout_diff_pt"] = 100 * (turnout_comp["current_turnout"] - turnout_comp["previous_turnout"])

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
    by_code = {str(r["municipality_code"]): r for _, r in msum.iterrows()}
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
        lines = []
        if grp is not None and total > 0:
            for _, c in grp.iterrows():
                pct = 100 * c["current_votes"] / total
                lines.append(f"{c['candidate_name']}　{int(c['current_votes']):,}票　{pct:.1f}%")
        else:
            lines.append("未開票")
        hover = (
            f"<b>{r['municipality_name']}</b><br>"
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
        if sub.empty:
            continue
        sizes = 8 + 42 * (sub["remaining_votes"].astype(float) / max(max_value, 1)).pow(0.5)
        detail = (
            "<b style='font-size:16px'>" + sub["municipality_name"] + "</b><br>"
            + "<span style='font-size:15px'><b>推定残票 " + sub["remaining_votes"].map(lambda x: f"{x:,.0f}") + "票</b></span><br>"
            + "<span style='font-size:14px'>開票率 " + sub["reporting_pct"].map(lambda x: f"{x:.1f}%")
            + "　/　開票済み " + sub["reported_votes"].map(lambda x: f"{x:,.0f}") + "票"
            + "　/　最終総数 " + sub["final_valid_votes"].map(lambda x: f"{x:,.0f}") + "票</span><br><br>"
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

def render_candidate_totals(totals):
    html = []
    for _, r in totals.iterrows():
        color = candidate_color(r["attribute"])
        html.append(f"""
        <div class="result-card" style="border-left:7px solid {color}; padding-left:12px;">
          <div style="display:grid;grid-template-columns:1.5fr .8fr .65fr;gap:10px;align-items:end;">
            <div>
              <span class="candidate-name">{r['candidate_name']}</span>{attribute_badge(r['attribute'])}<br>
              <span class="candidate-party">{r['party'] or r['attribute']}</span>
            </div>
            <div class="big-num">{int(r['current_votes']):,}</div>
            <div class="pct-num">{float(r['pct']):.2f}%</div>
          </div>
          <div class="progress-outer"><div class="progress-inner" style="width:{min(float(r['pct']),100):.2f}%;background:{color};"></div></div>
        </div>
        """)
    return "\n".join(html)

def guide_cards(msum, swing):
    cards = []
    used = set()
    a = msum.sort_values("remaining_votes", ascending=False).iloc[0]
    used.add(a["municipality_code"])
    cards.append((a["municipality_name"], f"推定残票 {int(a['remaining_votes']):,}票",
                  f"県内で最も多く票が残る地点。現在の開票率は {a['reporting_pct']:.1f}%、{a['leader_name']} が {int(a['lead_votes']):,}票リードしています。"))
    q = msum[(msum["reporting_pct"] >= 50) & (~msum["municipality_code"].isin(used))]
    if not q.empty:
        b = q.sort_values("lead_points").iloc[0]
        used.add(b["municipality_code"])
        cards.append((b["municipality_name"], f"差は {b['lead_points']:.1f}ポイント",
                      f"開票が半分以上進んだ市町村の中で接戦。{b['leader_name']} が {int(b['lead_votes']):,}票差で先行しています。"))
    q2 = swing[(swing["reporting_pct"] >= 90) & (~swing["municipality_code"].isin(used))]
    if not q2.empty:
        c = q2.loc[q2["shift"].abs().idxmax()]
        direction = "保守" if c["shift"] > 0 else "オール沖縄"
        cards.append((c["municipality_name"], f"{direction}方向へ {abs(c['shift']):.1f}pt",
                      f"比較選挙からの保革マージン変化が大きい市町村。開票率は {c['reporting_pct']:.1f}%です。"))
    return cards

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

# -------------------- data --------------------
results, elections, turnout, municipalities, geojson, layout_boxes = load_all()

with st.sidebar:
    st.markdown("### デモ設定")
    global_pct = st.slider("擬似・全県開票進行", 0, 100, 72, 1)

    current_meta = elections[elections["election_id"] == CURRENT_ELECTION].iloc[0]
    prior = elections[elections["date_serial"] < current_meta["date_serial"]].copy()
    prior = prior.sort_values("date_serial", ascending=False)
    prior["label"] = prior.apply(election_label, axis=1)
    compare_options = prior[["label", "election_id"]]
    default_idx = compare_options["election_id"].tolist().index("GOV2018") if "GOV2018" in compare_options["election_id"].tolist() else 0
    compare_label = st.selectbox("比較する過去選挙", compare_options["label"].tolist(), index=default_idx)
    compare_id = compare_options.loc[compare_options["label"] == compare_label, "election_id"].iloc[0]

    swing_threshold = st.select_slider("シフト表示の最低開票率", options=[50, 75, 90, 95, 100], value=50)
    sort_mode = st.selectbox("市町村一覧の並べ替え", ["得票規模", "開票率", "リード票", "接戦順", "残票"])
    st.caption("地図は本島を中央、周辺離島を外周インセットへ再配置した沖縄県模式図です。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。")

current, msum, totals, overall_reporting = simulate_snapshot(results, municipalities, global_pct)
compare_detail, swing = compare_context(results, turnout, current, msum, compare_id)
state_shift = statewide_margin_current(current) - statewide_margin_final(results, compare_id)
global_max_shift = max(float(swing["shift"].abs().max()) if not swing.empty else 1.0, 1.0)

# -------------------- page --------------------
st.markdown('<span class="live-badge">開票速報</span><span class="demo-badge">2022実績を使ったデモ</span>', unsafe_allow_html=True)
st.markdown('<div class="nyt-title" style="font-size:2.25rem;margin-top:8px;">沖縄県知事選 開票速報</div>', unsafe_allow_html=True)
st.markdown('<div class="kicker">2022年9月11日投開票の確定結果を擬似開票に変換した試作版です。本番ではリアルタイム入力値に置き換わります。</div>', unsafe_allow_html=True)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)

leader = totals.iloc[0] if not totals.empty and totals["current_votes"].sum() else None
state_tie = (
    len(totals) >= 2 and int(totals.iloc[0]["current_votes"]) == int(totals.iloc[1]["current_votes"])
) if leader is not None else False
leader_color = "#8E8E8E" if state_tie else (candidate_color(leader["attribute"]) if leader is not None else "#808080")
leader_name = "同数" if state_tie else (leader["candidate_name"] if leader is not None else "未開票")
banner_label = "現在のリード" if overall_reporting < 99.95 else "確定結果"

st.markdown(
    f"""
<div class="winner-banner" style="background:{leader_color};">
  <div class="winner-small">{banner_label}</div>
  <div class="winner-main">{leader_name}</div>
</div>
<div class="stat-strip">
  <span>全県開票率 <strong>{overall_reporting:.1f}%</strong></span>
  <span>開票済み <strong>{int(msum['reported_votes'].sum()):,}票</strong></span>
  <span>推定残票 <strong>{int(msum['remaining_votes'].sum()):,}票</strong></span>
  <span>比較 <strong>{compare_label}</strong></span>
</div>
""",
    unsafe_allow_html=True
)

left, right = st.columns([1.05, 1.15], gap="large")
with left:
    st.markdown('<div class="eyebrow">全県集計</div>', unsafe_allow_html=True)
    st.markdown(render_candidate_totals(totals), unsafe_allow_html=True)
    st.caption("得票率は現時点で開票済みの候補者票を分母に計算。")

with right:
    st.markdown('<div class="eyebrow">市町村別マップ</div>', unsafe_allow_html=True)
    map_mode = st.radio("表示切替", ["得票シェア", "リード票", "推定残票"], horizontal=True, label_visibility="collapsed")
    lead_max = float(msum["lead_votes"].max()) if len(msum) else 1
    remain_max = float(msum["remaining_votes"].max()) if len(msum) else 1
    if map_mode == "得票シェア":
        render_boxed_map(winner_map_panel, geojson, layout_boxes, 610, "winner", msum, current, compare_detail, compare_label)
        st.markdown('<div class="map-caption">本島を中央、周辺離島を外周の枠へ配置した模式図。濃い赤・濃い青ほどリード幅が大きく、淡い色ほど接戦を示します。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。</div>', unsafe_allow_html=True)
    elif map_mode == "リード票":
        render_boxed_map(lead_bubble_panel, geojson, layout_boxes, 520, "lead", msum, max_value=lead_max)
        st.markdown('<div class="map-caption">円の大きさ＝1位と2位の票差。本島・離島をまたいで同じサイズ基準を使います。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。</div>', unsafe_allow_html=True)
    else:
        render_boxed_map(remaining_bubble_panel, geojson, layout_boxes, 520, "remain", msum, compare_detail, compare_label, max_value=remain_max)
        st.markdown('<div class="map-caption">円の大きさ＝推定残票。ポップアップには投票率、前回選比、比較選挙の勝敗差も表示します。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">41市町村の開票状況</div>', unsafe_allow_html=True)
st.markdown('<div class="section-deck">リードポイント、リード票、開票率、開票済み票、推定残票を一つの表で追います。</div>', unsafe_allow_html=True)

tbl = msum.copy()
tbl["リード"] = tbl.apply(lambda r: "未開票" if r["reported_votes"] == 0 else f"{r['leader_name']} +{r['lead_points']:.1f}pt", axis=1)
tbl["リード票"] = tbl["lead_votes"].astype(int)
tbl["開票率"] = tbl["reporting_pct"]
tbl["開票済み票"] = tbl["reported_votes"].astype(int)
tbl["推定残票"] = tbl["remaining_votes"].astype(int)
tbl["接戦度"] = tbl["lead_points"].abs()
tbl = tbl.merge(swing[["municipality_code", "current_margin"]], on="municipality_code", how="left")
if sort_mode == "得票規模":
    tbl = tbl.sort_values("final_valid_votes", ascending=False)
elif sort_mode == "開票率":
    tbl = tbl.sort_values("開票率", ascending=False)
elif sort_mode == "リード票":
    # 保革（オール沖縄・革新 対 保守）の軸で符号付きに並べる。
    # 上ほどオール沖縄・革新が優位、下ほど保守が優位。表示は実際にリードした候補者名のまま。
    tbl = tbl.sort_values("current_margin", ascending=True)
elif sort_mode == "接戦順":
    tbl = tbl[tbl["reported_votes"] > 0].sort_values("接戦度", ascending=True)
elif sort_mode == "残票":
    tbl = tbl.sort_values("推定残票", ascending=False)

table_show = tbl[["municipality_name", "リード", "リード票", "開票率", "開票済み票", "推定残票"]].rename(columns={"municipality_name": "市町村"})

main_table, guides = st.columns([2.25, 1.0], gap="large")
with main_table:
    st.dataframe(
        table_show, hide_index=True, use_container_width=True, height=560,
        column_config={
            "リード票": st.column_config.NumberColumn(format="%d"),
            "開票率": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            "開票済み票": st.column_config.NumberColumn(format="%d"),
            "推定残票": st.column_config.NumberColumn(format="%d"),
        },
    )
with guides:
    st.markdown("### 注目市町村")
    for title, metric, copy in guide_cards(msum, swing):
        st.markdown(
            f"""
<div class="guide-card">
  <div class="guide-title">{title}</div>
  <div class="guide-metric">{metric}</div>
  <div class="guide-copy">{copy}</div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown('<div class="section-title">過去選挙からどちらへ動いたか</div>', unsafe_allow_html=True)
direction = "保守" if state_shift > 0 else "オール沖縄"
direction_color = RED if state_shift > 0 else BLUE
st.markdown(
    f'<div class="section-deck"><strong>{compare_label}</strong> と現在の保革マージンを比較。県全体では <span style="color:{direction_color};font-weight:800;">{direction}方向へ {abs(state_shift):.1f}pt</span>。地図は開票率 {swing_threshold}% 以上の市町村のみ表示します。</div>',
    unsafe_allow_html=True
)

s_left, s_right = st.columns([1.1, 1.0], gap="large")
with s_left:
    render_boxed_map(shift_map_panel, geojson, layout_boxes, 510, "shift", swing, swing_threshold, global_max_shift)
    st.markdown(
        f'<div class="legend-row"><span style="color:{RED};font-weight:800;">→ 保守方向</span><span style="color:{BLUE};font-weight:800;">← 革新・オール沖縄方向</span></div>',
        unsafe_allow_html=True
    )
with s_right:
    comp = swing[swing["reporting_pct"] >= swing_threshold].copy()
    comp["今回マージン"] = comp["current_margin"].map(lambda x: f"保守 +{x:.1f}" if x >= 0 else f"オール沖縄 +{abs(x):.1f}")
    comp["比較選挙マージン"] = comp["previous_margin"].map(lambda x: f"保守 +{x:.1f}" if x >= 0 else f"オール沖縄 +{abs(x):.1f}")
    comp["シフト"] = comp["shift"].map(lambda x: f"保守へ +{x:.1f}" if x >= 0 else f"オール沖縄へ +{abs(x):.1f}")
    comp["開票率"] = comp["reporting_pct"]
    comp = comp.sort_values("shift", key=lambda s: s.abs(), ascending=False)
    st.dataframe(
        comp[["municipality_name", "今回マージン", "比較選挙マージン", "シフト", "開票率"]].rename(columns={"municipality_name": "市町村"}),
        hide_index=True, use_container_width=True, height=560,
        column_config={"開票率": st.column_config.NumberColumn(format="%.1f%%")},
    )

st.markdown('<div class="sub-rule"></div>', unsafe_allow_html=True)
st.caption("試作版 v0.5｜赤＝保守系、青＝オール沖縄系。現在の数字は2022年確定結果から生成した擬似開票データであり、実際の2022年開票推移ではありません。")
