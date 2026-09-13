
from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

BLUE = "#1675B9"
RED = "#C93238"
GRAY = "#8E8E8E"
BLUE_LIGHT = "#DDEAF6"
RED_LIGHT = "#F4DBDD"

CANDIDATE_COLOR = {"永原稔": BLUE, "山本敬三郎": RED, "元場鉄太郎": GRAY}

PLOT_CONFIG = {
    "scrollZoom": True,
    "doubleClick": "reset+autosize",
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines"],
}

st.markdown(
    """
<style>
html, body, [class*="css"] { font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:#292929; }
.block-container { max-width:1460px; padding-top:.6rem; padding-bottom:4rem; }
.portal-nav-spacer { height:.15rem; }
.portal-breadcrumb { color:#777; font-size:.82rem; padding-top:.68rem; white-space:nowrap; }
#MainMenu, footer, header[data-testid="stHeader"] { display:none !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; }
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {
  position:sticky; top:0; z-index:999; background:#fff; padding-bottom:.3rem;
}
.page-kicker { font-size:.78rem; font-weight:800; letter-spacing:.11em; color:#666; margin-top:.3rem; }
.page-title { font-family:Georgia,"Yu Mincho",serif; font-size:2.3rem; font-weight:800; letter-spacing:-.02em; margin-top:.15rem; }
.deck { color:#6B6B6B; font-size:.94rem; margin-top:.35rem; }
.top-rule { border-top:4px solid #111; margin:10px 0 14px; }
.section-title { font-family:Georgia,"Yu Mincho",serif; font-size:1.5rem; font-weight:800; margin:1.5rem 0 .1rem; }
.section-deck { color:#6B6B6B; font-size:.92rem; margin-bottom:.6rem; }
.candidate-card { display:flex; align-items:center; gap:.8rem; border:1px solid #E4E4E4; border-left:6px solid #ccc; padding:.7rem .9rem; margin-bottom:.5rem; }
.candidate-name { font-size:1.08rem; font-weight:800; }
.candidate-party { color:#6B6B6B; font-size:.85rem; }
.candidate-votes { margin-left:auto; text-align:right; }
.candidate-votes .n { font-size:1.15rem; font-weight:800; font-variant-numeric:tabular-nums; }
.candidate-votes .p { color:#6B6B6B; font-size:.82rem; }
.result-badge { display:inline-block; font-size:.68rem; font-weight:800; padding:.12rem .5rem; border-radius:3px; margin-left:.5rem; vertical-align:middle; }
.legend-row { display:flex; gap:16px; align-items:center; font-size:.8rem; color:#666; margin:.3rem 0 .6rem; flex-wrap:wrap; }
.legend-dot { display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:5px; vertical-align:middle; }
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container,
.js-plotly-plot .nsewdrag, .js-plotly-plot svg { touch-action:none !important; }
.js-plotly-plot .modebar { transform:scale(1.35); transform-origin:top right; }
.js-plotly-plot .modebar-btn { padding:3px !important; }
table.sz-table { border-collapse:collapse; font-size:.84rem; width:100%; }
table.sz-table th { background:#222; color:#fff; padding:6px 9px; text-align:left; font-weight:700; }
table.sz-table td { padding:5px 9px; border-bottom:1px solid #eee; }
table.sz-table td.meta { color:#555; font-size:.8rem; background:#fafafa; }
table.sz-table td.cell { color:#fff; font-weight:700; text-align:center; }
.sz-table-wrap { overflow-x:auto; border:1px solid #ddd; margin-bottom:1rem; }
@media(max-width:800px) {
  .block-container { padding-left:.7rem; padding-right:.7rem; padding-top:.6rem !important; }
  .page-title { font-size:1.6rem; }
  .section-title { font-size:1.25rem; }
}
</style>
""",
    unsafe_allow_html=True,
)

nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_shizuoka", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 静岡県 過去の選挙</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)
st.caption("v0.9.31 · SHIZUOKA")

st.markdown('<div class="page-kicker">SHIZUOKA ELECTION ARCHIVE</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">静岡県　過去の選挙</div>', unsafe_allow_html=True)
st.markdown('<div class="deck">静岡県の過去の選挙を、市町村別・郡別の地図と一覧表で見るアーカイブです。</div>', unsafe_allow_html=True)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)


@st.cache_data
def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_all():
    muni = pd.DataFrame(load_json("shizuoka1974_municipalities_v1.json"))
    gun = pd.DataFrame(load_json("shizuoka1974_gun_v1.json"))
    pref = load_json("shizuoka1974_prefecture_v1.json")
    geo_muni = load_json("shizuoka_1975.geojson")
    geo_gun = load_json("shizuoka_1975_gun.geojson")
    return muni, gun, pref, geo_muni, geo_gun


muni, gun, pref, geo_muni, geo_gun = load_all()

ELECTIONS = {"SHZ_GOV1974": "1974年 静岡県知事選"}
election_label = st.selectbox("対象選挙", list(ELECTIONS.values()), index=0)
st.caption("現在は1974年知事選のみ収録しています。今後、他の年・選挙種別を追加予定です。")


def blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t); g = round(g1 + (g2 - g1) * t); b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def cell_color(winner, margin_pt):
    base = CANDIDATE_COLOR.get(winner, GRAY)
    t = min(abs(float(margin_pt)) / 25.0, 1.0)
    if winner == "永原稔":
        return blend(BLUE_LIGHT, BLUE, t)
    if winner == "山本敬三郎":
        return blend(RED_LIGHT, RED, t)
    return "#E3E3E3"


# ---------------- 県計サマリー ----------------
st.markdown('<div class="section-title">県全体の結果</div>', unsafe_allow_html=True)
st.caption(f"投票日 {pref['election_date']} ／ 当日有権者数 {pref['eligible_voters']:,}人 ／ 投票率 {pref['turnout_rate']*100:.2f}%")

for c in pref["candidates"]:
    color = CANDIDATE_COLOR.get(c["name"], GRAY)
    badge_color = {"当選": "#1E7A34", "次点": "#946200", "落選": "#8E8E8E"}.get(c["result"], "#8E8E8E")
    st.markdown(
        f"""
<div class="candidate-card" style="border-left-color:{color};">
  <div>
    <span class="candidate-name">{c['name']}</span>
    <span class="result-badge" style="background:{badge_color};color:#fff;">{c['result']}</span><br>
    <span class="candidate-party">{c['party']}</span>
  </div>
  <div class="candidate-votes">
    <div class="n">{c['votes']:,}票</div>
    <div class="p">{c['pct']*100:.2f}%</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# ---------------- 地図 ----------------
st.markdown('<div class="section-title">地図</div>', unsafe_allow_html=True)
map_unit = st.radio("表示単位", ["市町村別", "郡別"], horizontal=True, key="sz_map_unit")


def _geometry_xy(geometry):
    xs, ys = [], []
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polygons = coords if gtype == "MultiPolygon" else [coords]
    for polygon in polygons:
        if not polygon:
            continue
        exterior = polygon[0]
        xs.extend([p[0] for p in exterior] + [None])
        ys.extend([p[1] for p in exterior] + [None])
    return xs, ys


def _bounds_of_geojson(gj):
    xs, ys = [], []
    for f in gj["features"]:
        x, y = _geometry_xy(f["geometry"])
        xs += [v for v in x if v is not None]
        ys += [v for v in y if v is not None]
    return min(xs), max(xs), min(ys), max(ys)


def _finish_map(fig, gj, height=620, pad=0.03):
    minx, maxx, miny, maxy = _bounds_of_geojson(gj)
    dx = max(maxx - minx, 1e-6); dy = max(maxy - miny, 1e-6)
    fig.update_xaxes(range=[minx - dx * pad, maxx + dx * pad], visible=False, fixedrange=False, constrain="domain")
    fig.update_yaxes(range=[miny - dy * pad, maxy + dy * pad], visible=False, fixedrange=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        dragmode="pan", hovermode="closest", showlegend=False, uirevision=True,
        hoverlabel=dict(bgcolor="white", bordercolor="#C9C9C9",
                         font=dict(family="Meiryo, Yu Gothic, sans-serif", size=13, color="#303030"),
                         align="left", namelength=0),
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


def _polygon_centroid(geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polys = coords if gtype == "MultiPolygon" else [coords]
    best = None
    for poly in polys:
        if not poly:
            continue
        ring = poly[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        area = 0.0
        for i in range(len(ring) - 1):
            area += xs[i] * ys[i+1] - xs[i+1] * ys[i]
        area = abs(area) / 2
        if best is None or area > best[0]:
            best = (area, sum(xs) / len(xs), sum(ys) / len(ys))
    return (best[1], best[2]) if best else (0, 0)


def _candidate_breakdown_html(r):
    valid = float(r["valid_votes"]) if r["valid_votes"] else 0
    lines = []
    for label, col in [("永原稔", "votes_nagahara"), ("山本敬三郎", "votes_yamamoto"), ("元場鉄太郎", "votes_motoba")]:
        v = float(r[col])
        pct = (v / valid * 100) if valid else 0
        lines.append(f"{label}　{int(v):,}票（{pct:.1f}%）")
    return "<br>".join(lines)


def muni_map_panel(gj, mdf, height=620):
    by_name = mdf.set_index("municipality_name")
    fig = go.Figure()
    for feature in gj["features"]:
        name = feature["properties"]["municipality_name"]
        xs, ys = _geometry_xy(feature["geometry"])
        if name not in by_name.index:
            fill, hover = "#EDEDED", f"<b>{name}</b><br>データなし"
        else:
            r = by_name.loc[name]
            fill = cell_color(r["winner"], r["margin_pt"])
            hover = (f"<b>{name}</b><br>{r['winner']}　+{r['margin_pt']:.1f}pt"
                      f"（+{int(r['margin_votes']):,}票）<br>"
                      f"{_candidate_breakdown_html(r)}")
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=fill,
            line=dict(color="white", width=1.0),
            text=hover, hovertemplate="%{text}<extra></extra>",
            hoveron="fills", showlegend=False, name="",
        ))
    return _finish_map(fig, gj, height=height)


def gun_map_panel(gj, gdf, height=620):
    by_name = gdf.set_index("gun_name")
    fig = go.Figure()
    for feature in gj["features"]:
        name = feature["properties"]["gun_name"]
        xs, ys = _geometry_xy(feature["geometry"])
        if name not in by_name.index:
            fill, hover = "#EDEDED", f"<b>{name}</b><br>データなし"
        else:
            r = by_name.loc[name]
            fill = cell_color(r["winner"], r["margin_pt"])
            hover = (f"<b>{name}</b><br>{r['winner']}　+{r['margin_pt']:.1f}pt"
                      f"（+{int(r['margin_votes']):,}票）<br>"
                      f"{_candidate_breakdown_html(r)}")
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=fill,
            line=dict(color="white", width=1.6),
            text=hover, hovertemplate="%{text}<extra></extra>",
            hoveron="fills", showlegend=False, name="",
        ))
    # 郡に属さない市部を薄く重ねて位置関係を示す
    for feature in geo_muni["features"]:
        if feature["properties"].get("gun"):
            continue
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor="#F2F2F2",
            line=dict(color="white", width=1.0),
            text=f"<b>{feature['properties']['municipality_name']}</b><br>市部(郡別集計の対象外)",
            hovertemplate="%{text}<extra></extra>", hoveron="fills", showlegend=False, name="",
        ))
    return _finish_map(fig, gj, height=height)


def lead_bubble_panel_muni(gj, mdf, height=620):
    d = mdf.copy()
    cx, cy = [], []
    for _, r in d.iterrows():
        feat = next((f for f in gj["features"] if f["properties"]["municipality_name"] == r["municipality_name"]), None)
        x, y = _polygon_centroid(feat["geometry"]) if feat else (None, None)
        cx.append(x); cy.append(y)
    d["x"], d["y"] = cx, cy
    d = d.dropna(subset=["x", "y"])
    max_v = max(d["margin_votes"].max(), 1)
    fig = go.Figure()
    for feature in gj["features"]:
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D4D4D4", width=0.7),
                                  fill="toself", fillcolor="#FAFAFA", hoverinfo="skip", showlegend=False, name=""))
    for winner, color in [("永原稔", BLUE), ("山本敬三郎", RED), ("元場鉄太郎", GRAY)]:
        sub = d[d["winner"] == winner]
        if sub.empty:
            continue
        sizes = 8 + 42 * (sub["margin_votes"].astype(float) / max_v).pow(0.5)
        detail = ("<b>" + sub["municipality_name"] + "</b><br>"
                  + sub["winner"] + " +" + sub["margin_votes"].map(lambda x: f"{x:,.0f}") + "票<br>"
                  + "リード差 " + sub["margin_pt"].map(lambda x: f"{x:.1f}pt") + "<br>"
                  + sub.apply(_candidate_breakdown_html, axis=1))
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers",
            marker=dict(size=sizes, color=color, opacity=0.4, line=dict(color=color, width=1.4)),
            text=detail, hovertemplate="%{text}<extra></extra>", showlegend=False, name="",
        ))
    return _finish_map(fig, gj, height=height)


def lead_bubble_panel_gun(gj, gdf, height=620):
    d = gdf.copy()
    cx, cy = [], []
    for _, r in d.iterrows():
        feat = next((f for f in gj["features"] if f["properties"]["gun_name"] == r["gun_name"]), None)
        x, y = _polygon_centroid(feat["geometry"]) if feat else (None, None)
        cx.append(x); cy.append(y)
    d["x"], d["y"] = cx, cy
    d = d.dropna(subset=["x", "y"])
    max_v = max(d["margin_votes"].max(), 1)
    fig = go.Figure()
    for feature in gj["features"]:
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D4D4D4", width=1.0),
                                  fill="toself", fillcolor="#FAFAFA", hoverinfo="skip", showlegend=False, name=""))
    for feature in geo_muni["features"]:
        if feature["properties"].get("gun"):
            continue
        xs, ys = _geometry_xy(feature["geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor="#F2F2F2",
                                  line=dict(color="white", width=1.0), hoverinfo="skip", showlegend=False, name=""))
    for winner, color in [("永原稔", BLUE), ("山本敬三郎", RED), ("元場鉄太郎", GRAY)]:
        sub = d[d["winner"] == winner]
        if sub.empty:
            continue
        sizes = 10 + 46 * (sub["margin_votes"].astype(float) / max_v).pow(0.5)
        detail = ("<b>" + sub["gun_name"] + "</b><br>"
                  + sub["winner"] + " +" + sub["margin_votes"].map(lambda x: f"{x:,.0f}") + "票<br>"
                  + "リード差 " + sub["margin_pt"].map(lambda x: f"{x:.1f}pt") + "<br>"
                  + sub.apply(_candidate_breakdown_html, axis=1))
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"], mode="markers",
            marker=dict(size=sizes, color=color, opacity=0.4, line=dict(color=color, width=1.4)),
            text=detail, hovertemplate="%{text}<extra></extra>", showlegend=False, name="",
        ))
    return _finish_map(fig, gj, height=height)


zoom_pct = st.slider("拡大", 100, 400, 100, step=20, key="sz-zoom", format="%d%%")
map_content = st.radio("表示内容", ["勝者マップ", "リード票マップ"], horizontal=True, key="sz_map_content")
if map_content == "勝者マップ":
    if map_unit == "市町村別":
        fig = muni_map_panel(geo_muni, muni)
    else:
        fig = gun_map_panel(geo_gun, gun)
else:
    if map_unit == "市町村別":
        fig = lead_bubble_panel_muni(geo_muni, muni)
    else:
        fig = lead_bubble_panel_gun(geo_gun, gun)
fig = apply_zoom(fig, zoom_pct / 100.0)
st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG, key="sz-map")

legend_note = "色の濃さ＝勝差の大きさ" if map_content == "勝者マップ" else "円の大きさ＝勝差(得票数)の大きさ"
st.markdown(
    f"""
<div class="legend-row">
  <span><span class="legend-dot" style="background:{BLUE};"></span>永原稔が優位</span>
  <span><span class="legend-dot" style="background:{RED};"></span>山本敬三郎が優位</span>
  <span><span class="legend-dot" style="background:{GRAY};"></span>元場鉄太郎が優位</span>
  <span>{legend_note}</span>
</div>
""",
    unsafe_allow_html=True,
)
st.caption("1本指で移動。地図の上にあるスライダーで拡大・縮小できます。「郡別」表示では、当時郡に属さなかった市部を薄いグレーで参考表示しています(郡別集計には含まれません)。")

# ---------------- 郡別集計テーブル ----------------
st.markdown('<div class="section-title">郡別集計</div>', unsafe_allow_html=True)
gun_rows = []
for _, r in gun.sort_values("gun_name").iterrows():
    color = cell_color(r["winner"], r["margin_pt"])
    gun_rows.append(
        f"<tr><td class='meta'><b>{r['gun_name']}</b></td>"
        f"<td class='cell' style='background:{color};'>{r['winner']} +{r['margin_pt']:.1f}pt<br>（+{int(r['margin_votes']):,}票）</td>"
        f"<td>{int(r['votes_nagahara']):,}</td><td>{int(r['votes_yamamoto']):,}</td>"
        f"<td>{int(r['votes_motoba']):,}</td><td>{int(r['valid_votes']):,}</td></tr>"
    )
gun_table = (
    '<div class="sz-table-wrap"><table class="sz-table">'
    "<tr><th>郡</th><th>最多得票</th><th>永原稔</th><th>山本敬三郎</th><th>元場鉄太郎</th><th>有効票計</th></tr>"
    + "".join(gun_rows) + "</table></div>"
)
st.markdown(gun_table, unsafe_allow_html=True)

# ---------------- 市町村別一覧 ----------------
st.markdown('<div class="section-title">市町村別一覧</div>', unsafe_allow_html=True)
st.markdown('<div class="section-deck">「市」は郡に属さないため郡列は空欄です。</div>', unsafe_allow_html=True)
sort_mode = st.selectbox("並び替え", ["郡順", "リード票順(永原→山本)"], key="sz_sort")
if sort_mode == "郡順":
    muni_sorted = muni.sort_values(["gun", "municipality_name"], na_position="first")
else:
    m = muni.copy()
    m["_signed"] = m["votes_yamamoto"].astype(float) - m["votes_nagahara"].astype(float)
    muni_sorted = m.sort_values("_signed", ascending=True)
muni_rows = []
for _, r in muni_sorted.iterrows():
    color = cell_color(r["winner"], r["margin_pt"])
    gun_disp = r["gun"] if pd.notna(r["gun"]) else "―"
    muni_rows.append(
        f"<tr><td class='meta'>{gun_disp}</td><td class='meta'><b>{r['municipality_name']}</b></td>"
        f"<td class='cell' style='background:{color};'>{r['winner']} +{r['margin_pt']:.1f}pt<br>（+{int(r['margin_votes']):,}票）</td>"
        f"<td>{int(r['votes_nagahara']):,}</td><td>{int(r['votes_yamamoto']):,}</td>"
        f"<td>{int(r['votes_motoba']):,}</td><td>{int(r['valid_votes']):,}</td></tr>"
    )
muni_table = (
    '<div class="sz-table-wrap"><table class="sz-table">'
    "<tr><th>郡</th><th>市町村</th><th>最多得票</th><th>永原稔</th><th>山本敬三郎</th><th>元場鉄太郎</th><th>有効票計</th></tr>"
    + "".join(muni_rows) + "</table></div>"
)
st.markdown(muni_table, unsafe_allow_html=True)
st.caption("出典: 静岡県選挙管理委員会『選挙結果調』(昭和49年)。元場鉄太郎の市町村別明細合計は原表県計と189票差があり、差の帰属先が原表で特定できないため配賦していません(データ提供者による注記)。")
