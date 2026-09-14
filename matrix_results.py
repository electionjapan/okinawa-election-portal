
from pathlib import Path
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

ATTR_COLOR = {
    "保守系": RED,
    "オール沖縄系": BLUE,
    "革新系（2014年以前）": BLUE,
    "第三極・その他政党": GRAY,
    "独立・無所属": GRAY,
    "民主系": GRAY,
    "公明党": RED,
    "革新分裂候補": GRAY,
}
BLUE_BLOC_ATTRS = ["オール沖縄系", "革新系（2014年以前）"]

DISTRICT_COLORS = {
    "沖縄県第1区": "#B8860B",
    "沖縄県第2区": "#2E8B57",
    "沖縄県第3区": "#6A5ACD",
    "沖縄県第4区": "#CC5500",
}

PLOT_CONFIG = {
    "scrollZoom": True,
    "doubleClick": "reset+autosize",
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines"],
}

# ---------------- style ----------------
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
.legend-row { display:flex; gap:16px; align-items:center; font-size:.8rem; color:#666; margin:.3rem 0 .6rem; flex-wrap:wrap; }
.legend-dot { display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:5px; vertical-align:middle; }
.legend-line { display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; border-radius:50%; margin-right:5px; vertical-align:middle; color:#fff; font-size:.68rem; font-weight:800; }
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container,
.js-plotly-plot .nsewdrag, .js-plotly-plot svg { touch-action:none !important; }
.js-plotly-plot .modebar { transform:scale(1.35); transform-origin:top right; }
.js-plotly-plot .modebar-btn { padding:3px !important; }
.matrix-table-wrap { overflow-x:auto; border:1px solid #ddd; }
table.matrix-table { border-collapse:collapse; font-size:.82rem; white-space:nowrap; width:100%; }
table.matrix-table th { background:#222; color:#fff; padding:6px 9px; text-align:left; position:sticky; top:0; z-index:2; font-weight:700; }
table.matrix-table td { padding:5px 9px; border-bottom:1px solid #eee; }
table.matrix-table td.meta { color:#555; font-size:.78rem; background:#fafafa; }
table.matrix-table td.cell { color:#fff; font-weight:700; text-align:center; }
table.matrix-table tr:hover td { filter:brightness(0.94); }
tr.pref-row td { position:sticky; top:26px; z-index:1; border-bottom:2px solid #222; background:#fafafa; }
tr.pref-row td.meta { background:#f2f2f2; }
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
    if st.button("← トップへ戻る", key="portal_back_matrix", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 41市町村 保守寄り？革新より？</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)
st.caption("v0.9.33 · NEW MAP · 模式配置")

st.markdown('<div class="page-kicker">OKINAWA ELECTION MATRIX</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">41市町村　保守寄り？革新より？</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="deck">知事選・参院選・衆院選をまたいで、市町村ごとにどちらの陣営がどれだけの差で勝ったかを一覧で比較します。</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)

# ---------------- data ----------------
@st.cache_data
def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_all():
    winners = pd.DataFrame(load_json("matrix_winners_v2.json"))
    elections = pd.DataFrame(load_json("matrix_elections_v2.json"))
    municipalities = pd.DataFrame(load_json("matrix_municipalities_v2.json"))
    geojson = load_json("map_layout_v0912.geojson")
    layout_boxes = load_json("map_layout_v0912.json")
    prefecture = {r["election_id"]: r for r in load_json("matrix_prefecture_v2.json")}
    return winners, elections, municipalities, geojson, layout_boxes, prefecture

winners, elections, municipalities, geojson, layout_boxes, prefecture = load_all()
elections = elections.sort_values(["year", "race_type"]).reset_index(drop=True)

def blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t); g = round(g1 + (g2 - g1) * t); b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def cell_color(attribute, margin_pt):
    if attribute == "同数" or abs(float(margin_pt)) < 1e-9:
        return "#BDBDBD"
    t = min(abs(float(margin_pt)) / 25.0, 1.0)
    if attribute == "保守系":
        return blend(RED_LIGHT, RED, t)
    if attribute in BLUE_BLOC_ATTRS:
        return blend(BLUE_LIGHT, BLUE, t)
    return "#E3E3E3"

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

def _bounds_of_geojson(gj):
    xs, ys = [], []
    for f in gj["features"]:
        x, y = _geometry_xy(f["geometry"])
        xs += [v for v in x if v is not None]
        ys += [v for v in y if v is not None]
    return min(xs), max(xs), min(ys), max(ys)

def _finish_panel_map(fig, gj, height=560, pad=0.025):
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

def add_layout_boxes(fig, lb):
    boxes = lb.get("boxes", {}); labels = lb.get("labels", {})
    for key, box in boxes.items():
        if key == "本島":
            continue
        x0, y0, x1, y1 = [float(v) for v in box]
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                       line=dict(color="#D8D8D8", width=1.0), fillcolor="rgba(255,255,255,0)", layer="below")
        label = labels.get(key)
        if label:
            fig.add_annotation(x=x0 + 1.0, y=y1 - 0.9, text=f"<b>{label}</b>", showarrow=False,
                                xanchor="left", yanchor="top",
                                font=dict(size=12, color="#666666", family="Meiryo, Yu Gothic, sans-serif"),
                                bgcolor="rgba(255,255,255,0.88)", borderpad=2)
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

muni_district = dict(zip(municipalities["municipality_name"], municipalities["hr_district"]))

DISTRICT_NUM = {"沖縄県第1区": "1", "沖縄県第2区": "2", "沖縄県第3区": "3", "沖縄県第4区": "4"}
_HONTO_BOX = layout_boxes.get("boxes", {}).get("本島", [29, 4, 70, 98])

def _is_on_honto(cx, cy, box=_HONTO_BOX):
    x0, y0, x1, y1 = box
    return x0 <= cx <= x1 and y0 <= cy <= y1

def _polygon_centroid(geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polys = [coords] if gtype == "Polygon" else coords
    best = None
    for poly in polys:
        ring = poly[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        area = 0.0
        for i in range(len(ring) - 1):
            area += xs[i] * ys[i+1] - xs[i+1] * ys[i]
        area = abs(area) / 2
        if best is None or area > best[0]:
            best = (area, sum(xs) / len(xs), sum(ys) / len(ys))
    return (best[1], best[2]) if best else (0, 0)

def _all_points(geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polys = [coords] if gtype == "Polygon" else coords
    pts = []
    for poly in polys:
        pts.extend(poly[0])
    return pts

def _edges_of(geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polys = [coords] if gtype == "Polygon" else coords
    segs = []
    for poly in polys:
        ring = poly[0]
        for i in range(len(ring) - 1):
            a = (round(ring[i][0], 4), round(ring[i][1], 4))
            b = (round(ring[i + 1][0], 4), round(ring[i + 1][1], 4))
            segs.append((a, b))
    return segs

def _segment_owner_map(gj):
    owner = {}
    for f in gj["features"]:
        name = f["properties"]["municipality_name"]
        for a, b in _edges_of(f["geometry"]):
            key = tuple(sorted([a, b]))
            owner.setdefault(key, []).append(name)
    return owner

def matrix_map_panel(gj, wsub, race_type, height=560):
    by_name = {r["municipality_name"]: r for _, r in wsub.iterrows()}
    fig = go.Figure()
    mk_x, mk_y, mk_color, mk_text = [], [], [], []
    mainland_pts_by_district = {}
    for feature in gj["features"]:
        name = feature["properties"]["municipality_name"]
        r = by_name.get(name)
        xs, ys = _geometry_xy(feature["geometry"])
        if r is None:
            fill = "#EDEDED"
            hover = f"<b>{name}</b><br>データなし"
        else:
            fill = cell_color(r["winner_attr"], r["margin_pt"])
            hover = (f"<b>{name}</b><br>{r['winner_name']}　+{r['margin_pt']:.1f}pt"
                      f"（+{int(r['margin_votes']):,}票）")
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=fill,
            line=dict(color="white", width=1.1),
            text=hover, hovertemplate="%{text}<extra></extra>",
            hoveron="fills", showlegend=False, name="",
        ))
        if race_type == "HR":
            dist = muni_district.get(name)
            cx, cy = _polygon_centroid(feature["geometry"])
            if _is_on_honto(cx, cy):
                mainland_pts_by_district.setdefault(dist, []).extend(_all_points(feature["geometry"]))
            else:
                mk_x.append(cx); mk_y.append(cy)
                mk_color.append(DISTRICT_COLORS.get(dist, GRAY))
                mk_text.append(DISTRICT_NUM.get(dist, "?"))
    if race_type == "HR":
        # 隣接する市町村同士の共有辺のうち、区が異なる境界だけを太線で描く(実際の区境そのもの)
        owner = _segment_owner_map(gj)
        for seg, names in owner.items():
            if len(names) != 2:
                continue
            n1, n2 = names
            d1, d2 = muni_district.get(n1), muni_district.get(n2)
            if d1 and d2 and d1 != d2:
                (ax, ay), (bx, by) = seg
                fig.add_trace(go.Scatter(
                    x=[ax, bx], y=[ay, by], mode="lines",
                    line=dict(color="#222222", width=3.6),
                    hoverinfo="skip", showlegend=False, name="",
                ))
        # 本島側の各区は、その区域の中心に番号バッジを1つ表示
        for dist, pts in mainland_pts_by_district.items():
            color = DISTRICT_COLORS.get(dist, GRAY)
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            fig.add_annotation(
                x=cx, y=cy, text=f"<b>{DISTRICT_NUM.get(dist,'?')}</b>",
                showarrow=False, font=dict(size=14, color="white", family="Meiryo, Yu Gothic, sans-serif"),
                bgcolor=color, bordercolor="white", borderwidth=1.4, borderpad=4,
            )
    if race_type == "HR" and mk_x:
        fig.add_trace(go.Scatter(
            x=mk_x, y=mk_y, mode="markers+text",
            marker=dict(size=15, color=mk_color, line=dict(color="white", width=1.2)),
            text=mk_text, textfont=dict(size=9, color="white", family="Meiryo, Yu Gothic, sans-serif"),
            hoverinfo="skip", showlegend=False, name="",
        ))
    return _finish_panel_map(fig, gj, height=height)

def render_boxed_map(panel_fn, gj, lb, height, key_prefix, *args, **kwargs):
    zoom_pct = st.slider("拡大", 100, 400, 100, step=20, key=f"{key_prefix}-zoom", format="%d%%")
    fig = panel_fn(gj, *args, height=height, **kwargs)
    fig = add_layout_boxes(fig, lb)
    fig = apply_zoom(fig, zoom_pct / 100.0)
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG, key=f"{key_prefix}-boxed")

# ---------------- election selector ----------------
st.markdown('<div class="section-title">対象選挙を選ぶ</div>', unsafe_allow_html=True)
st.markdown('<div class="section-deck">知事選・参院選・衆院選から自由に組み合わせて選べます。</div>', unsafe_allow_html=True)

type_label = {"GOV": "知事選", "SEN": "参院選", "HR": "衆院選"}
elections["display_label"] = elections.apply(lambda r: f"{r['year']}{type_label[r['race_type']]}", axis=1)
label_to_id = dict(zip(elections["display_label"], elections["election_id"]))

sel_cols = st.columns(3)
selected_ids = []
for i, rtype in enumerate(["GOV", "SEN", "HR"]):
    sub = elections[elections["race_type"] == rtype]
    with sel_cols[i]:
        picked = st.multiselect(
            type_label[rtype], sub["display_label"].tolist(),
            default=sub["display_label"].tolist(), key=f"pick_{rtype}",
        )
        selected_ids += [label_to_id[p] for p in picked]

selected_elections = elections[elections["election_id"].isin(selected_ids)].sort_values(["year", "race_type"])

if selected_elections.empty:
    st.info("表示する選挙を1つ以上選んでください。")
    st.stop()

# ---------------- map ----------------
st.markdown('<div class="section-title">市町村別マップ</div>', unsafe_allow_html=True)
map_label = st.selectbox("地図に表示する選挙", selected_elections["display_label"].tolist(),
                          index=len(selected_elections) - 1)
map_eid = label_to_id[map_label]
map_race_type = elections.loc[elections["election_id"] == map_eid, "race_type"].iloc[0]
wsub_map = winners[winners["election_id"] == map_eid]

render_boxed_map(matrix_map_panel, geojson, layout_boxes, 560, "matrix-map", wsub_map, map_race_type)

legend_html = (
    '<div class="legend-row">'
    f'<span><span class="legend-dot" style="background:{RED};"></span>保守系が優位</span>'
    f'<span><span class="legend-dot" style="background:{BLUE};"></span>オール沖縄・革新が優位</span>'
    f'<span><span class="legend-dot" style="background:{GRAY};"></span>その他の系統</span>'
    '<span>色の濃さ＝勝差の大きさ</span>'
)
if map_race_type == "HR":
    for dist, c in DISTRICT_COLORS.items():
        n = DISTRICT_NUM.get(dist, "?")
        legend_html += f'<span><span class="legend-line" style="background:{c};">{n}</span>{dist}</span>'
legend_html += "</div>"
st.markdown(legend_html, unsafe_allow_html=True)
st.caption("1本指で移動。地図の上にあるスライダーで拡大・縮小できます。衆院選を選んだときは、本島側は区が変わる境界そのものを太線で示し、各区の中心に番号を表示します。離島側は各市町村に番号マーカーを重ねて小選挙区の区割りを示します。")

# ---------------- table ----------------
st.markdown('<div class="section-title">市町村別一覧</div>', unsafe_allow_html=True)
st.markdown('<div class="section-deck">左端は地域区分と衆院小選挙区。表の先頭「沖縄県全体」行は、その選挙で県全体では誰が何ポイント差(何票差)で勝ったか。「全体傾向」は選んだ選挙の中でその市町村がどちらの陣営に多く投票したかの通算です。各セルは勝った候補者名(名字)・ポイント差・(得票差)です。</div>', unsafe_allow_html=True)

muni_order = municipalities.sort_values(["region8_order", "region8_suborder"])
cols_eids = selected_elections["election_id"].tolist()
cols_labels = selected_elections["display_label"].tolist()

pivot = {}
for eid in cols_eids:
    sub = winners[winners["election_id"] == eid].set_index("municipality_name")
    pivot[eid] = sub

def camp_of(attr):
    if attr == "保守系":
        return "保守"
    if attr in BLUE_BLOC_ATTRS:
        return "オール沖縄・革新"
    return "その他"

def pref_cell_html(eid):
    p = prefecture.get(eid)
    if p is None:
        return '<td class="cell" style="background:#EDEDED;color:#999;">―</td>'
    if p["kind"] == "single":
        color = cell_color(p["winner_attr"], p["margin_pt"])
        text = f"{p['winner_surname']} +{p['margin_pt']:.1f}pt<br>（+{int(p['margin_votes']):,}票）"
        return f'<td class="cell" style="background:{color};">{text}</td>'
    # 衆院選: 4小選挙区の当選者と陣営別議席数
    camp = p["seat_camp"]
    top_camp = max(camp, key=camp.get)
    tie = sum(1 for v in camp.values() if v == camp[top_camp]) > 1 and camp[top_camp] > 0
    if tie or top_camp == "その他":
        color = "#BDBDBD" if tie else "#E3E3E3"
    else:
        color = blend(RED_LIGHT, RED, 0.55) if top_camp == "保守" else blend(BLUE_LIGHT, BLUE, 0.55)
    seat_line = f"保守{camp['保守']} オール沖縄{camp['オール沖縄・革新']}議席"
    who_line = "　".join(f"{s['district'][-2:-1]}区:{s['winner_surname']}" for s in p["seats"])
    text = f"{seat_line}<br>{who_line}"
    return f'<td class="cell" style="background:{color};font-size:.74rem;">{text}</td>'

pref_row_html = (
    '<tr class="pref-row"><td class="meta"><b>―</b></td><td class="meta">―</td><td class="meta"><b>沖縄県全体</b></td>'
    '<td class="cell" style="background:#222;color:#fff;">全県集計</td>'
    + "".join(pref_cell_html(eid) for eid in cols_eids)
    + "</tr>"
)

rows_html = [pref_row_html]
for _, m in muni_order.iterrows():
    name = m["municipality_name"]

    camp_wins = {"保守": 0, "オール沖縄・革新": 0, "その他": 0}
    n_total = 0
    for eid in cols_eids:
        sub = pivot[eid]
        if name in sub.index:
            camp_wins[camp_of(sub.loc[name]["winner_attr"])] += 1
            n_total += 1
    if n_total == 0:
        overall_html = '<td class="cell" style="background:#EDEDED;color:#999;">―</td>'
    else:
        top_camp = max(camp_wins, key=camp_wins.get)
        top_n = camp_wins[top_camp]
        tie = sum(1 for v in camp_wins.values() if v == top_n) > 1 and top_n > 0
        if tie or top_camp == "その他":
            overall_color = "#BDBDBD" if tie else "#E3E3E3"
            overall_label = "拮抗" if tie else "その他"
        else:
            t = top_n / n_total
            overall_color = blend(RED_LIGHT, RED, t) if top_camp == "保守" else blend(BLUE_LIGHT, BLUE, t)
            overall_label = top_camp
        overall_html = f'<td class="cell" style="background:{overall_color};">{overall_label}<br>{top_n}/{n_total}選挙</td>'

    tds = [
        f'<td class="meta">{m["region8"]}</td>',
        f'<td class="meta">{m["hr_district"]}</td>',
        f'<td class="meta"><b>{name}</b></td>',
        overall_html,
    ]
    for eid in cols_eids:
        sub = pivot[eid]
        if name not in sub.index:
            tds.append('<td class="cell" style="background:#EDEDED;color:#999;">―</td>')
            continue
        r = sub.loc[name]
        color = cell_color(r["winner_attr"], r["margin_pt"])
        text = f"{r['winner_surname']} +{r['margin_pt']:.1f}pt<br>（+{int(r['margin_votes']):,}票）"
        tds.append(f'<td class="cell" style="background:{color};">{text}</td>')
    rows_html.append(f"<tr>{''.join(tds)}</tr>")

header = (
    '<tr><th>地域区分</th><th>衆院小選挙区</th><th>市町村</th><th>全体傾向</th>'
    + "".join(f"<th>{lbl}</th>" for lbl in cols_labels)
    + "</tr>"
)
table_html = (
    '<div class="matrix-table-wrap"><table class="matrix-table">'
    + header + "".join(rows_html) + "</table></div>"
)
st.markdown(table_html, unsafe_allow_html=True)
st.caption("政治属性が「保守系」「オール沖縄系」「革新系（2014年以前）」以外の候補(第三極・独立・無所属など)が勝った場合はグレー表示です。「全体傾向」は選んだ選挙のうち、その市町村でどちらの陣営が多く勝ったかを示します(同数の場合は拮抗)。衆院選は4つの小選挙区で別々の当選者が出るため県全体で1人が勝つ形にはならず、「沖縄県全体」行では陣営別の獲得議席数と、各区の当選者(名字)を表示しています。")
