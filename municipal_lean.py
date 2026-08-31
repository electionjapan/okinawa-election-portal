from pathlib import Path
import html
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

RED = "#C93238"
BLUE = "#1675B9"
PURPLE = "#7C5AA6"
GREEN = "#3F7F6A"
ORANGE = "#C87921"
GRAY = "#8E8E8E"
DARK = "#292929"

ATTR_COLOR = {
    "保守系": RED,
    "公明党": RED,
    "オール沖縄系": BLUE,
    "革新系（2014年以前）": BLUE,
    "革新分裂候補": PURPLE,
    "民主系": GREEN,
    "第三極・その他政党": ORANGE,
    "独立・無所属": GRAY,
    "同数": GRAY,
}
REGION_ORDER = ["北部", "中部", "南部", "宮古", "八重山"]
TYPE_ORDER = ["知事選", "参院選", "衆院選"]

PLOT_CONFIG = {
    "scrollZoom": True,
    "doubleClick": "reset+autosize",
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines"],
}

# -------- portal navigation --------
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)
nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_lean", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル / 41市町村の政治傾向</div>', unsafe_allow_html=True)
st.caption("v0.9.13 · MUNICIPALITY TREND MATRIX")

st.markdown(
    """
<style>
html, body, [class*="css"] { font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:#292929; }
.block-container { max-width:1540px; padding-top:.6rem; padding-bottom:4rem; }
.portal-nav-spacer { height:.15rem; }
.portal-breadcrumb { color:#777; font-size:.82rem; padding-top:.68rem; white-space:nowrap; }
#MainMenu, footer, header[data-testid="stHeader"] { display:none !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; }
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {
  position:sticky; top:0; z-index:999; background:#fff; padding-bottom:.3rem;
}
.page-kicker { font-size:.78rem; font-weight:800; letter-spacing:.09em; color:#666; }
.page-title { font-family:Georgia,"Yu Mincho",serif; font-size:2.25rem; font-weight:800; letter-spacing:-.025em; line-height:1.1; }
.deck { color:#666; font-size:.94rem; line-height:1.7; margin-top:.35rem; }
.top-rule { border-top:4px solid #111; margin:10px 0 14px; }
.filter-box { border:1px solid #ddd; background:#f7f7f5; padding:10px 12px; border-radius:5px; }
.section-title { font-family:Georgia,"Yu Mincho",serif; font-size:1.55rem; font-weight:800; margin:1.55rem 0 .15rem; }
.section-deck { color:#6B6B6B; font-size:.92rem; margin-bottom:.65rem; }
.legend-row { display:flex; flex-wrap:wrap; gap:14px; align-items:center; font-size:.82rem; color:#666; margin:.25rem 0 .65rem; }
.legend-dot { width:10px; height:10px; display:inline-block; border-radius:2px; margin-right:4px; }
.matrix-wrap { overflow:auto; max-height:760px; border:1px solid #d8d8d8; background:white; position:relative; }
.matrix { border-collapse:separate; border-spacing:0; width:max-content; min-width:100%; font-size:12px; }
.matrix th, .matrix td { border-right:1px solid #e2e2e2; border-bottom:1px solid #e8e8e8; padding:7px 7px; vertical-align:middle; }
.matrix thead th { position:sticky; top:0; z-index:30; background:#f1f1ef; font-weight:800; text-align:center; white-space:nowrap; border-bottom:2px solid #bbb; }
.matrix .region-col { position:sticky; left:0; z-index:20; min-width:58px; width:58px; text-align:center; font-weight:800; background:#f7f7f5; }
.matrix .district-col { position:sticky; left:58px; z-index:20; min-width:62px; width:62px; text-align:center; font-weight:700; background:#fafafa; }
.matrix .muni-col { position:sticky; left:120px; z-index:20; min-width:92px; width:92px; font-weight:800; background:#fff; box-shadow:3px 0 3px rgba(0,0,0,.04); }
.matrix thead .region-col, .matrix thead .district-col, .matrix thead .muni-col { z-index:40; background:#ececea; }
.matrix .election-col { min-width:138px; width:138px; text-align:center; }
.matrix .cell-top { font-weight:850; font-size:12px; line-height:1.25; white-space:nowrap; }
.matrix .cell-bottom { font-size:10.5px; line-height:1.3; margin-top:3px; white-space:nowrap; }
.matrix tr.region-start td { border-top:3px solid #aaa; }
.matrix .head-year { font-size:13px; font-weight:850; }
.matrix .head-type { font-size:10.5px; color:#666; margin-top:2px; }
.note-box { background:#f7f7f7; border:1px solid #ddd; padding:10px 13px; font-size:.84rem; color:#666; border-radius:5px; }
.js-plotly-plot .modebar { transform:scale(1.25); transform-origin:top right; }
.js-plotly-plot .modebar-btn { padding:3px !important; }
@media(max-width:800px) {
  .block-container { padding-left:.65rem; padding-right:.65rem; padding-top:.6rem !important; }
  .portal-breadcrumb { padding-top:.35rem; font-size:.76rem; white-space:normal; line-height:1.35; }
  .page-title { font-size:1.75rem; }
  .matrix-wrap { max-height:650px; }
  .matrix .region-col { min-width:52px; width:52px; }
  .matrix .district-col { left:52px; min-width:56px; width:56px; }
  .matrix .muni-col { left:108px; min-width:82px; width:82px; }
  .matrix .election-col { min-width:126px; width:126px; }
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
    winners = pd.DataFrame(load_json("municipal_winners.json"))
    elections = pd.DataFrame(load_json("comparison_elections.json"))
    municipalities = pd.DataFrame(load_json("municipalities.json"))
    geojson = load_json("map_layout_v0912.geojson")
    layout = load_json("map_layout_v0912.json")
    boundaries = load_json("house_district_boundaries_v0913.geojson")
    district_labels = load_json("house_district_labels_v0913.json")
    return winners, elections, municipalities, geojson, layout, boundaries, district_labels

def hex_to_rgb(h):
    h=h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def rgb_to_hex(rgb):
    return "#"+"".join(f"{max(0,min(255,int(round(v)))):02X}" for v in rgb)

def blend(c1,c2,t):
    a=hex_to_rgb(c1); b=hex_to_rgb(c2)
    return rgb_to_hex(tuple(a[i]+(b[i]-a[i])*t for i in range(3)))

def cell_colors(attribute, point_diff):
    base=ATTR_COLOR.get(attribute,GRAY)
    # small leads are very light; 30pt+ is close to the base color
    t=.16 + .72*min(abs(float(point_diff))/30.0,1.0)
    bg=blend("#FFFFFF",base,t)
    fg="#FFFFFF" if t>.59 else DARK
    return bg,fg

def fmt_votes(v):
    v=float(v)
    if abs(v-round(v))<1e-6:
        return f"{int(round(v)):,}"
    return f"{v:,.3f}".rstrip("0").rstrip(".")

def district_short(s):
    return str(s).replace("沖縄県第", "").replace("区", "区")

def _geometry_xy(geometry):
    xs,ys=[],[]
    gtype=geometry.get("type")
    coords=geometry.get("coordinates",[])
    if gtype in ("Polygon","MultiPolygon"):
        polygons=[coords] if gtype=="Polygon" else coords
        for polygon in polygons:
            if not polygon: continue
            ext=polygon[0]
            xs.extend([p[0] for p in ext]+[None]); ys.extend([p[1] for p in ext]+[None])
    elif gtype in ("LineString","MultiLineString"):
        lines=[coords] if gtype=="LineString" else coords
        for line in lines:
            if not line: continue
            xs.extend([p[0] for p in line]+[None]); ys.extend([p[1] for p in line]+[None])
    return xs,ys

def _bounds(geojson):
    xs,ys=[],[]
    for f in geojson["features"]:
        x,y=_geometry_xy(f["geometry"])
        xs.extend([v for v in x if v is not None]); ys.extend([v for v in y if v is not None])
    return min(xs),max(xs),min(ys),max(ys)

def add_layout_boxes(fig,layout):
    for key,box in layout.get("boxes",{}).items():
        if key=="本島": continue
        x0,y0,x1,y1=[float(v) for v in box]
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,line=dict(color="#D7D7D7",width=1),fillcolor="rgba(255,255,255,0)",layer="below")
        label=layout.get("labels",{}).get(key)
        if label:
            fig.add_annotation(x=x0+.8,y=y1-.6,text=f"<b>{label}</b>",showarrow=False,xanchor="left",yanchor="top",font=dict(size=11,color="#666"),bgcolor="rgba(255,255,255,.88)",borderpad=2)
    return fig

def map_figure(geojson,layout,boundaries,district_labels,selected):
    bycode={str(r["municipality_code"]):r for _,r in selected.iterrows()}
    fig=go.Figure()
    for feature in geojson["features"]:
        code=str(feature["properties"]["municipality_code"])
        r=bycode.get(code)
        if r is None: continue
        xs,ys=_geometry_xy(feature["geometry"])
        bg,_=cell_colors(r["attribute"],r["point_diff"])
        hover=(
            f"<b>{html.escape(str(r['municipality_name']))}</b>"
            f"<br>{html.escape(str(r['winner_name']))}（{html.escape(str(r['attribute_short']))}）"
            f"<br><b>+{float(r['point_diff']):.1f}pt</b> / {fmt_votes(r['vote_diff'])}票差"
            f"<br>衆院 {district_short(r['house_district'])}"
        )
        fig.add_trace(go.Scatter(x=xs,y=ys,mode="lines",fill="toself",fillcolor=bg,line=dict(color="#FFFFFF",width=.7),text=hover,hovertemplate="%{text}<extra></extra>",hoveron="fills",showlegend=False,name=""))

    # Only the boundaries BETWEEN House districts are emphasized; coastlines remain light.
    for f in boundaries["features"]:
        xs,ys=_geometry_xy(f["geometry"])
        fig.add_trace(go.Scatter(x=xs,y=ys,mode="lines",line=dict(color="#202020",width=3.2),hoverinfo="skip",showlegend=False,name=""))
    for p in district_labels:
        fig.add_annotation(x=float(p["label_x"]),y=float(p["label_y"]),text=f"<b>{p['label']}</b>",showarrow=False,font=dict(size=11,color="#111"),bgcolor="rgba(255,255,255,.84)",bordercolor="#555",borderwidth=.7,borderpad=2)

    fig=add_layout_boxes(fig,layout)
    minx,maxx,miny,maxy=_bounds(geojson); dx=max(maxx-minx,1e-6); dy=max(maxy-miny,1e-6)
    fig.update_xaxes(range=[minx-dx*.025,maxx+dx*.025],visible=False,fixedrange=False,constrain="domain")
    fig.update_yaxes(range=[miny-dy*.025,maxy+dy*.025],visible=False,fixedrange=False,scaleanchor="x",scaleratio=1)
    fig.update_layout(height=620,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor="white",plot_bgcolor="white",dragmode="pan",hovermode="closest",showlegend=False,uirevision=True,hoverlabel=dict(bgcolor="white",bordercolor="#C9C9C9",font=dict(family="Meiryo, Yu Gothic, sans-serif",size=13,color="#303030"),align="left",namelength=0))
    return fig

def matrix_html(winners,municipalities,election_meta,election_ids):
    rows=municipalities.copy()
    rows["region_rank"]=rows["region"].map({x:i for i,x in enumerate(REGION_ORDER)})
    rows["district_rank"]=rows["house_district"].str.extract(r"第(\d)区")[0].astype(int)
    rows=rows.sort_values(["region_rank","district_rank","sort_no"])
    lookup={(str(r["municipality_code"]),r["election_id"]):r for _,r in winners.iterrows()}
    meta=election_meta.set_index("election_id")

    parts=['<div class="matrix-wrap"><table class="matrix"><thead><tr>']
    parts += ['<th class="region-col">地域</th>','<th class="district-col">衆院区</th>','<th class="muni-col">市町村</th>']
    for eid in election_ids:
        m=meta.loc[eid]
        parts.append(f'<th class="election-col"><div class="head-year">{int(m["year"])}</div><div class="head-type">{html.escape(str(m["type"]))}</div></th>')
    parts.append('</tr></thead><tbody>')

    prev_region=None
    for _,mr in rows.iterrows():
        region=str(mr["region"]); cls=' class="region-start"' if prev_region is not None and region!=prev_region else ''
        parts.append(f'<tr{cls}>')
        parts.append(f'<td class="region-col">{html.escape(region)}</td>')
        parts.append(f'<td class="district-col">{html.escape(district_short(mr["house_district"]))}</td>')
        parts.append(f'<td class="muni-col">{html.escape(str(mr["municipality_name"]))}</td>')
        for eid in election_ids:
            r=lookup.get((str(mr["municipality_code"]),eid))
            if r is None:
                parts.append('<td class="election-col" style="background:#f5f5f5;color:#999;">―</td>')
                continue
            bg,fg=cell_colors(r["attribute"],r["point_diff"])
            top=f'{html.escape(str(r["winner_surname"]))} +{float(r["point_diff"]):.1f}pt'
            bottom=f'{html.escape(str(r["attribute_short"]))}（{fmt_votes(r["vote_diff"])}票差）'
            title=f'{r["municipality_name"]} / {meta.loc[eid,"label"]} / {r["winner_name"]} / {r["attribute"]}'
            parts.append(f'<td class="election-col" title="{html.escape(str(title))}" style="background:{bg};color:{fg};"><div class="cell-top">{top}</div><div class="cell-bottom">{bottom}</div></td>')
        parts.append('</tr>'); prev_region=region
    parts.append('</tbody></table></div>')
    return ''.join(parts)

# -------- data --------
winners,elections,municipalities,geojson,layout,boundaries,district_labels=load_all()
elections=elections.sort_values("date_serial").reset_index(drop=True)

# -------- page --------
st.markdown('<div class="page-kicker">OKINAWA MUNICIPALITY TREND MATRIX</div>',unsafe_allow_html=True)
st.markdown('<div class="page-title">41市町村　保守寄り？革新寄り？</div>',unsafe_allow_html=True)
st.markdown('<div class="deck">知事選・参院選・衆院小選挙区について、各市町村で「どの系統の候補が、何ポイント・何票差で1位だったか」を横断して見ます。セルの色は1位候補の政治属性、色の濃さは1位と2位の得票率差です。</div>',unsafe_allow_html=True)
st.markdown('<div class="top-rule"></div>',unsafe_allow_html=True)

f1,f2=st.columns([1.05,1.4],gap="large")
with f1:
    types=st.multiselect("対象選挙",TYPE_ORDER,default=TYPE_ORDER)
    min_year,max_year=int(elections["year"].min()),int(elections["year"].max())
    years=st.slider("年代",min_year,max_year,(min_year,max_year),step=1)
with f2:
    filtered=elections[elections["type"].isin(types) & elections["year"].between(years[0],years[1])].copy()
    labels=filtered["label"].tolist()
    shown_labels=st.multiselect("表に表示する選挙",labels,default=labels)
    shown=filtered[filtered["label"].isin(shown_labels)].copy().sort_values("date_serial")

if shown.empty:
    st.warning("表示する選挙を1つ以上選んでください。")
    st.stop()

# map election selector; default newest among displayed elections
st.markdown('<div class="section-title">選択した選挙の市町村別地図</div>',unsafe_allow_html=True)
map_label=st.selectbox("地図に表示する選挙",shown["label"].tolist(),index=len(shown)-1)
map_eid=shown.loc[shown["label"]==map_label,"election_id"].iloc[0]
selected=winners[winners["election_id"]==map_eid].copy()
st.plotly_chart(map_figure(geojson,layout,boundaries,district_labels,selected),use_container_width=True,config=PLOT_CONFIG,key="lean-map")
st.markdown('<div class="section-deck">太い黒線は衆院小選挙区（1～4区）の区割り。市町村の色は1位候補の系統、濃さは2位との差を示します。右上の＋／－で拡大縮小できます。</div>',unsafe_allow_html=True)

legend_items=[("保守系",RED),("オール沖縄／革新",BLUE),("革新分裂",PURPLE),("民主系",GREEN),("第三極",ORANGE),("独立・その他",GRAY)]
legend=''.join(f'<span><i class="legend-dot" style="background:{c};"></i>{t}</span>' for t,c in legend_items)
st.markdown(f'<div class="legend-row">{legend}</div>',unsafe_allow_html=True)

st.markdown('<div class="section-title">41市町村 × 選挙　勝者マトリクス</div>',unsafe_allow_html=True)
st.markdown('<div class="section-deck">横にスクロールできます。セルの1行目は「名字＋ポイント差」、2行目は「系統（票差）」。地域区分は沖縄県の5圏域（北部・中部・南部・宮古・八重山）です。</div>',unsafe_allow_html=True)

ids=shown["election_id"].tolist()
st.markdown(matrix_html(winners,municipalities,elections,ids),unsafe_allow_html=True)

st.markdown(
    '<div class="note-box" style="margin-top:10px;"><b>ポイント差の定義：</b>市町村ごとに、1位候補の得票率－2位候補の得票率。分母はその市町村の有効投票数です。衆院選は各市町村が属する小選挙区の候補者同士を比較しています。背景色は候補者の政治属性であり、「市町村そのものの思想」を断定するものではありません。</div>',
    unsafe_allow_html=True,
)
