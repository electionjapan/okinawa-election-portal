"""
沖縄県知事選 開票マップ【実寸版】（ポータル内の新ページ）

沖縄本島・宮古・八重山・大東など、41市町村を実際の位置関係・距離感に近い形で
表示する地図ページ。既存の模式地図(map_layout_v0912.geojson)は使用しない。

live_data.py（Googleスプレッドシート読み取り・集計）は既存の開票速報ページと共通で
使うが、地図・レイアウト・色分けロジックはこのファイル単体で完結している。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import live_data as ld

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
TIE_GRAY = "#BDBDBD"
OTHER_GRAY = "#E3E3E3"
BLUE_BLOC_ATTRS = ["オール沖縄系", "革新系（2014年以前）"]

MAP_STYLE = "open-street-map"  # MapLibre / トークン不要

QUICK_ZOOM_GROUPS = {
    "全県": None,
    "沖縄本島周辺": ["本島・近隣", "西部離島"],
    "宮古": ["宮古"],
    "八重山": ["八重山"],
    "大東": ["大東"],
}


# ---------------- data ----------------
@st.cache_data
def load_geojson():
    with open(DATA_DIR / "okinawa_municipalities_real_distance_approx_v2.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_meta():
    with open(DATA_DIR / "realmap_municipalities_v1.json", encoding="utf-8") as f:
        return json.load(f)


def validate_geojson(geo, meta):
    problems = []
    features = geo.get("features", [])
    if len(features) != 41:
        problems.append(f"features数が41ではありません（{len(features)}件）")
    codes = [f["properties"].get("municipality_code") for f in features]
    if len(set(codes)) != 41:
        problems.append(f"ユニークなmunicipality_codeが41ではありません（{len(set(codes))}件）")
    names = [f["properties"].get("municipality_name") for f in features]
    if len(set(names)) != 41:
        problems.append(f"ユニークなmunicipality_nameが41ではありません（{len(set(names))}件）")
    meta_codes = {m["municipality_code"] for m in meta}
    if meta_codes != set(codes):
        problems.append("メタデータとGeoJSONのmunicipality_codeが一致しません")
    return problems


def _geometry_lonlat(geometry):
    lons, lats = [], []
    gtype = geometry.get("type")
    polys = geometry.get("coordinates", [])
    polys = [polys] if gtype == "Polygon" else polys if gtype == "MultiPolygon" else []
    for poly in polys:
        if not poly:
            continue
        ring = poly[0]
        lons.extend([p[0] for p in ring] + [None])
        lats.extend([p[1] for p in ring] + [None])
    return lons, lats


def full_bounds(geo):
    all_lons, all_lats = [], []
    for f in geo["features"]:
        lons, lats = _geometry_lonlat(f["geometry"])
        all_lons += [v for v in lons if v is not None]
        all_lats += [v for v in lats if v is not None]
    return min(all_lons), max(all_lons), min(all_lats), max(all_lats)


def group_bounds(geo, meta, group_names):
    if group_names is None:
        return full_bounds(geo)
    target_names = {m["municipality_name"] for m in meta if m["display_group"] in group_names}
    lons, lats = [], []
    for f in geo["features"]:
        if f["properties"]["municipality_name"] not in target_names:
            continue
        lo, la = _geometry_lonlat(f["geometry"])
        lons += [v for v in lo if v is not None]
        lats += [v for v in la if v is not None]
    if not lons:
        return full_bounds(geo)
    return min(lons), max(lons), min(lats), max(lats)


def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t); g = round(g1 + (g2 - g1) * t); b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def lead_fill_color(attribute, lead_points, reported_votes):
    """既存の開票速報ページ（live_results.py）と同じ考え方の色分け。"""
    if reported_votes is None or reported_votes <= 0:
        return GRAY_LIGHT
    if attribute == "同数" or abs(float(lead_points)) < 1e-12:
        return TIE_GRAY
    t = min(abs(lead_points) / 25.0, 1.0)
    if attribute == "保守系":
        return _blend(RED_LIGHT, RED, t)
    if attribute in BLUE_BLOC_ATTRS:
        return _blend(BLUE_LIGHT, BLUE, t)
    return OTHER_GRAY


def _hover_text(name, row, current_group):
    status = row.get("status", "未開票")
    reporting_pct = row.get("reporting_pct")
    reporting_txt = "―" if pd.isna(reporting_pct) else f"{float(reporting_pct):.1f}%"
    lines = [f"<b>{name}</b>", f"開票率 {reporting_txt}"]
    if status == "確定":
        lines.append("<b>開票確定</b>")
    if current_group is not None and len(current_group) > 0 and float(row.get("reported_votes") or 0) > 0:
        grp = current_group.sort_values(["current_votes"], ascending=False)
        top = grp.iloc[0]
        lines.append(f"首位　{top['candidate_name']}")
        lines.append(f"得票　{int(top['current_votes']):,}票")
        if len(grp) > 1:
            second = grp.iloc[1]
            diff_votes = int(top["current_votes"] - second["current_votes"])
            total = float(grp["current_votes"].sum())
            diff_pt = 100 * diff_votes / total if total > 0 else 0.0
            lines.append(f"2位　{second['candidate_name']}")
            if diff_votes == 0:
                lines.append("差　同数")
            else:
                lines.append(f"差　{diff_votes:,}票（+{diff_pt:.1f}pt）")
    else:
        lines.append("未開票")
    return "<br>".join(lines)


def build_map_figure(geo, msum, current, bounds, height, show_labels):
    by_code = {str(r["municipality_code"]): r for _, r in msum.iterrows()} if not msum.empty else {}
    current_groups = {str(c): g for c, g in current.groupby("municipality_code")} if not current.empty else {}

    fig = go.Figure()
    label_lons, label_lats, label_texts = [], [], []

    for feature in geo["features"]:
        props = feature["properties"]
        code = str(props["municipality_code"])
        name = props["municipality_name"]
        row = by_code.get(code)

        lons, lats = _geometry_lonlat(feature["geometry"])
        if row is None:
            fill = GRAY_LIGHT
            hover = f"<b>{name}</b><br>データを取得できませんでした"
        else:
            fill = lead_fill_color(row.get("leader_attribute", ""), row.get("lead_points", 0), row.get("reported_votes"))
            hover = _hover_text(name, row, current_groups.get(code))

        fig.add_trace(go.Scattermap(
            lon=lons, lat=lats, mode="lines", fill="toself", fillcolor=fill,
            line=dict(color="white", width=1.2),
            text=hover, hovertemplate="%{text}<extra></extra>",
            showlegend=False, name="",
        ))

        if show_labels:
            label_lon = props.get("label_lon")
            label_lat = props.get("label_lat")
            if label_lon is not None and label_lat is not None:
                label_lons.append(label_lon)
                label_lats.append(label_lat)
                label_texts.append(name)

    if show_labels and label_lons:
        fig.add_trace(go.Scattermap(
            lon=label_lons, lat=label_lats, mode="text", text=label_texts,
            textfont=dict(size=10, color="#222"), hoverinfo="skip", showlegend=False, name="",
        ))

    x0, x1, y0, y1 = bounds
    center_lon, center_lat = (x0 + x1) / 2, (y0 + y1) / 2
    lon_span = max(x1 - x0, 0.05)
    zoom = 8.5 - (lon_span ** 0.42) * 2.0
    zoom = max(4.0, min(11.0, zoom))

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        map=dict(style=MAP_STYLE, center=dict(lon=center_lon, lat=center_lat), zoom=zoom),
        uirevision="okinawa-real-map-view",
        showlegend=False,
    )
    return fig


# ---------------- style ----------------
st.markdown(
    """
<style>
html, body, [class*="css"] { font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:#292929; }
.block-container { max-width:1200px; padding-top:.6rem; padding-bottom:4rem; }
.portal-nav-spacer { height:.15rem; }
.portal-breadcrumb { color:#777; font-size:.82rem; padding-top:.68rem; white-space:nowrap; }
#MainMenu, footer, header[data-testid="stHeader"] { display:none !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; }
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {
  position:sticky; top:0; z-index:999; background:#fff; padding-bottom:.3rem;
}
.page-title { font-family:Georgia,"Yu Mincho",serif; font-size:2.1rem; font-weight:800; margin-top:.2rem; }
.deck { color:#6B6B6B; font-size:.92rem; margin-top:.3rem; }
.top-rule { border-top:4px solid #111; margin:10px 0 18px; }
.rm-why { background:#f5f5f5; border-left:4px solid #999; padding:8px 12px; font-size:.85rem; color:#555; margin:.5rem 0 1rem; }
.rm-stat-strip { display:flex; gap:18px; flex-wrap:wrap; font-size:.92rem; color:#333; margin:.4rem 0 1rem; }
.rm-stat-strip strong { font-size:1.05rem; }
.rm-cand-row { display:flex; gap:16px; flex-wrap:wrap; margin:.3rem 0 1rem; }
.rm-cand-chip { border-left:5px solid #999; padding:4px 10px; background:#fafafa; font-size:.88rem; border-radius:2px; }
.rm-footnote { color:#888; font-size:.74rem; margin-top:1rem; line-height:1.6; border-top:1px solid #eee; padding-top:.6rem; }
@media(max-width:800px){
  .block-container{padding-left:.7rem;padding-right:.7rem;padding-top:.6rem !important;}
  .page-title{font-size:1.4rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_realmap", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 開票マップ【実寸版】</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)

if st_autorefresh is not None:
    st_autorefresh(interval=20 * 1000, limit=None, key="realmap-autorefresh")

st.markdown('<div class="page-title">沖縄県知事選 開票マップ【実寸版】</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="deck">沖縄本島・宮古・八重山・大東など、島々の実際の位置関係に近い形で表示しています。</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="rm-why">一般的な選挙地図では、離島を見やすく並べ替えることがあります。'
    'この地図では、沖縄県の広さを実感できるよう、島々を実際の位置関係に近い形で表示しています'
    '（沖縄本島が相対的に小さく見えるのは仕様です）。</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)

geo = load_geojson()
meta = load_meta()
meta_df = pd.DataFrame(meta)
meta_df["municipality_code"] = meta_df["municipality_code"].astype(str)

problems = validate_geojson(geo, meta)
if problems:
    st.warning("地図データの検証で問題が見つかりました：\n- " + "\n- ".join(problems))


@st.cache_data(ttl=15, show_spinner=False)
def load_live():
    book = ld.load_google_workbook()
    return ld.build_live_models(book, meta_df[["municipality_code", "municipality_name"]])


fetch_error = None
try:
    models = load_live()
    st.session_state["realmap_models_cache"] = models
except Exception as e:
    fetch_error = str(e)
    models = st.session_state.get("realmap_models_cache")

if models is None:
    st.error("速報データを取得できませんでした。")
    msum = pd.DataFrame()
    current = pd.DataFrame()
    overall_reporting = None
    latest_update = "―"
    totals = pd.DataFrame()
else:
    if fetch_error:
        st.warning("直近のデータ取得に失敗したため、前回正常取得できたデータを表示しています。")
    msum = models.msum
    current = models.current
    overall_reporting = models.overall_reporting
    latest_update = models.latest_update
    totals = models.totals

reporting_txt = "―" if overall_reporting is None else f"{overall_reporting:.1f}%"
st.markdown(
    f'<div class="rm-stat-strip">'
    f'<span>最新更新　<strong>{latest_update}</strong></span>'
    f'<span>県全体開票率　<strong>{reporting_txt}</strong></span>'
    f"</div>",
    unsafe_allow_html=True,
)

if not totals.empty:
    chips = []
    for _, r in totals.iterrows():
        color = RED if r["attribute"] == "保守系" else (BLUE if r["attribute"] in BLUE_BLOC_ATTRS else GRAY)
        chips.append(
            f'<div class="rm-cand-chip" style="border-left-color:{color};">{r["candidate_name"]}　{int(r["current_votes"]):,}票</div>'
        )
    st.markdown(f'<div class="rm-cand-row">{"".join(chips)}</div>', unsafe_allow_html=True)

ctrl_left, ctrl_right = st.columns([1.4, 1.0])
with ctrl_left:
    zoom_choice = st.selectbox("クイックズーム", list(QUICK_ZOOM_GROUPS.keys()))
with ctrl_right:
    show_labels = st.checkbox("市町村名を表示", value=False)

bounds = group_bounds(geo, meta, QUICK_ZOOM_GROUPS[zoom_choice])
# StreamlitはUA判定ができないため、PC・スマホ双方である程度見やすい中間の高さを使う
map_height = 700
fig = build_map_figure(geo, msum, current, bounds, map_height, show_labels)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

st.markdown(
    """
<div class="rm-footnote">
※市町村境界はWeb表示用に簡略化しています。島々の位置関係・距離感を重視した表示です。<br>
開票データ：沖縄県選挙管理委員会公表資料をもとに集計<br>
地図：Web表示用簡略境界。島々の位置関係・距離感を重視した実寸近似表示
</div>
""",
    unsafe_allow_html=True,
)
