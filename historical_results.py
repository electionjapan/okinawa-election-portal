
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
    if st.button("← トップへ戻る", key="portal_back_history", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル / 過去の選挙結果</div>', unsafe_allow_html=True)
st.caption("v0.9.32 · NEW MAP · 模式配置")

st.markdown(
    """
<style>
html, body, [class*="css"] { font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:#292929; }
.block-container { max-width:1460px; padding-top:.6rem; padding-bottom:4rem; }
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
.page-kicker { font-size:.78rem; font-weight:800; letter-spacing:.08em; color:#666; }
.page-title { font-family:Georgia,"Yu Mincho",serif; font-size:2.35rem; font-weight:800; letter-spacing:-.02em; line-height:1.05; }
.deck { color:#6B6B6B; font-size:.94rem; margin-top:.35rem; }
.top-rule { border-top:4px solid #111; margin:10px 0 14px; }
.eyebrow { font-weight:800; font-size:.83rem; letter-spacing:.08em; color:#555; text-transform:uppercase; }
.section-title { font-family:Georgia,"Yu Mincho",serif; font-size:1.65rem; font-weight:800; margin:1.75rem 0 .1rem; }
.section-deck { color:#6B6B6B; font-size:.95rem; margin-bottom:.7rem; }
.result-card { border-top:1px solid #DADADA; padding:11px 2px 10px 2px; }
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
.stat-strip { display:flex; flex-wrap:wrap; gap:18px; background:#f3f3f3; border-top:1px solid #ddd; border-bottom:1px solid #ddd; padding:8px 13px; color:#666; font-size:.87rem; }
.stat-strip strong { color:#333; }
.note-box { background:#f7f7f7; border:1px solid #ddd; padding:10px 13px; color:#666; font-size:.86rem; border-radius:5px; }
.legend-row { display:flex; gap:18px; align-items:center; font-size:.82rem; color:#666; margin:.25rem 0 .5rem; }
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot .svg-container,
.js-plotly-plot .nsewdrag, .js-plotly-plot svg {
  touch-action: none !important;
}
.js-plotly-plot .modebar { transform: scale(1.35); transform-origin: top right; }
.js-plotly-plot .modebar-btn { padding: 3px !important; }
@media(max-width:800px) {
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
  .page-title { font-size:1.9rem; }
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
    return (
        pd.DataFrame(load_json("statewide_results.json")),
        pd.DataFrame(load_json("elections.json")),
        pd.DataFrame(load_json("turnout.json")),
        pd.DataFrame(load_json("municipalities.json")),
        load_json("map_layout_v0912.geojson"),
        load_json("map_layout_v0912.json"),
    )

def serial_to_date(v):
    return datetime(1899, 12, 30) + timedelta(days=float(v))

def short_label(row):
    dt = serial_to_date(row["date_serial"])
    typ = "知事選" if row["election_type"] == "知事選" else "参院選"
    return f"{dt.year} {typ}"

def full_label(row):
    dt = serial_to_date(row["date_serial"])
    return f"{dt:%Y年%m月%d日}　{row['election_name']}"

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0,min(255,int(round(v)))):02X}" for v in rgb)

def blend(c1, c2, t):
    r1,g1,b1 = hex_to_rgb(c1)
    r2,g2,b2 = hex_to_rgb(c2)
    return rgb_to_hex((r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t))

BLUE_BLOC_ATTRS = ["オール沖縄系", "革新系（2014年以前）"]

def candidate_color(attribute):
    return ATTR_COLOR.get(attribute, GRAY)

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

def is_blue_bloc(attribute):
    return attribute in BLUE_BLOC_ATTRS

def lead_fill_color(attribute, lead_points, valid_votes):
    if valid_votes <= 0:
        return GRAY_LIGHT
    if attribute == "同数" or abs(float(lead_points)) < 1e-12:
        return "#BDBDBD"
    t = min(abs(float(lead_points)) / 25.0, 1.0)
    if attribute == "保守系":
        return blend(RED_LIGHT, RED, t)
    if is_blue_bloc(attribute):
        return blend(BLUE_LIGHT, BLUE, t)
    return "#E3E3E3"

def _geometry_xy(geometry):
    xs, ys = [], []
    coords = geometry.get("coordinates", [])
    polygons = [coords] if geometry.get("type") == "Polygon" else coords if geometry.get("type") == "MultiPolygon" else []
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

def label_lookup(geojson):
    return pd.DataFrame([
        {
            "municipality_code": str(f["properties"]["municipality_code"]),
            "x": float(f["properties"].get("label_x", f["properties"].get("label_lon", 0))),
            "y": float(f["properties"].get("label_y", f["properties"].get("label_lat", 0))),
        }
        for f in geojson["features"]
    ])

def _bounds(geojson):
    xs, ys = [], []
    for f in geojson["features"]:
        x, y = _geometry_xy(f["geometry"])
        xs.extend([v for v in x if v is not None])
        ys.extend([v for v in y if v is not None])
    return (min(xs), max(xs), min(ys), max(ys)) if xs else (0,1,0,1)

def _finish_map(fig, geojson, height):
    minx,maxx,miny,maxy = _bounds(geojson)
    dx = max(maxx-minx, 1e-6)
    dy = max(maxy-miny, 1e-6)
    fig.update_xaxes(range=[minx-dx*.025,maxx+dx*.025], visible=False, fixedrange=False, constrain="domain")
    fig.update_yaxes(range=[miny-dy*.025,maxy+dy*.025], visible=False, fixedrange=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=height,
        margin=dict(l=0,r=0,t=0,b=0),
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

def election_snapshot(results, election_id, municipalities, turnout):
    d = results[results["election_id"] == election_id].copy()
    valid = d.groupby(["municipality_code","municipality_name"], as_index=False)["valid_votes"].first()

    leader_rows = []
    for code, grp in d.groupby("municipality_code"):
        grp = grp.sort_values("votes", ascending=False)
        top = grp.iloc[0]
        second = grp.iloc[1] if len(grp) > 1 else None
        topv = float(top["votes"])
        secondv = float(second["votes"]) if second is not None else 0.0
        tie = second is not None and abs(topv-secondv) < 1e-9
        diff = 0.0 if tie else topv-secondv
        total = float(top["valid_votes"])
        leader_rows.append({
            "municipality_code": code,
            "leader_name": "同数" if tie else top["candidate_name"],
            "leader_attribute": "同数" if tie else top["attribute"],
            "lead_votes": diff,
            "lead_points": 100*diff/total if total else 0.0,
            "is_tie": tie,
        })

    summary = (
        valid.merge(pd.DataFrame(leader_rows), on="municipality_code", how="left")
        .merge(municipalities, on=["municipality_code","municipality_name"], how="left")
    )

    t = turnout[turnout["election_id"] == election_id][["municipality_code","turnout_rate"]].copy()
    summary = summary.merge(t, on="municipality_code", how="left")

    totals = (
        d.groupby(["candidate_id","candidate_name","party","attribute","result"], as_index=False)["votes"]
        .sum().sort_values("votes", ascending=False)
    )
    total_votes = totals["votes"].sum()
    totals["pct"] = 100*totals["votes"]/total_votes if total_votes else 0.0
    state_tie = len(totals)>=2 and abs(float(totals.iloc[0]["votes"])-float(totals.iloc[1]["votes"]))<1e-9

    return d, summary, totals, state_tie

def winner_map_panel(geojson, summary, results_election, height=500):
    by_code = {str(r["municipality_code"]): r for _,r in summary.iterrows()}
    groups = {str(code):grp.sort_values("votes",ascending=False) for code,grp in results_election.groupby("municipality_code")}
    fig = go.Figure()
    for f in geojson["features"]:
        code = str(f["properties"]["municipality_code"])
        r = by_code.get(code)
        if r is None:
            continue
        grp = groups[code]
        total = float(grp["valid_votes"].iloc[0])
        lines = [
            f"{c['candidate_name']}　{float(c['votes']):,.0f}票　{100*float(c['votes'])/total:.1f}%"
            for _,c in grp.iterrows()
        ]
        lead_line = "<br><b>同数</b>" if r["leader_attribute"]=="同数" else f"<br>勝者　{r['leader_name']}　+{float(r['lead_votes']):,.0f}票 / +{r['lead_points']:.1f}pt"
        hover = (
            f"<b>{r['municipality_name']}</b>"
            + "<br><span style='color:#777'>確定結果</span>"
            + "<br>" + "<br>".join(lines)
            + "<br>────────────"
            + lead_line
        )
        x,y = _geometry_xy(f["geometry"])
        fig.add_trace(go.Scatter(
            x=x,y=y,mode="lines",fill="toself",
            fillcolor=lead_fill_color(r["leader_attribute"],r["lead_points"],total),
            line=dict(color="white",width=1.1),
            text=hover,hovertemplate="%{text}<extra></extra>",hoveron="fills",
            showlegend=False,name="",
        ))
    return _finish_map(fig,geojson,height)

def lead_bubble_panel(geojson, summary, height=420, global_max_lead=1):
    d = summary.merge(label_lookup(geojson), on="municipality_code", how="inner")
    fig = go.Figure()
    for f in geojson["features"]:
        x,y = _geometry_xy(f["geometry"])
        fig.add_trace(go.Scatter(x=x,y=y,mode="lines",line=dict(color="#D4D4D4",width=.7),hoverinfo="skip",showlegend=False,name=""))
    for attr,color in [("保守系",RED),("革新・オール沖縄",BLUE),("同数",GRAY),("その他","#B8B8B8")]:
        if attr=="同数":
            sub=d[d["leader_attribute"]=="同数"]
        elif attr=="革新・オール沖縄":
            sub=d[d["leader_attribute"].isin(BLUE_BLOC_ATTRS)]
        elif attr=="その他":
            sub=d[~d["leader_attribute"].isin(["保守系", *BLUE_BLOC_ATTRS, "同数"])]
        else:
            sub=d[d["leader_attribute"]==attr]
        if sub.empty:
            continue
        sizes = 8 + 42*(sub["lead_votes"].astype(float)/max(global_max_lead,1)).pow(.5)
        sizes = sizes.where(sub["leader_attribute"]!="同数",14)
        text = (
            "<b>"+sub["municipality_name"]+"</b>"
            + "<br><span style='color:#777'>勝者のリード</span>"
            + "<br><b>"+sub.apply(lambda r:"同数" if r["leader_attribute"]=="同数" else f"{r['leader_name']}　+{float(r['lead_votes']):,.0f}票",axis=1)+"</b>"
            + "<br>リード差　"+sub["lead_points"].map(lambda x:f"{x:.1f}pt")
        )
        fig.add_trace(go.Scatter(
            x=sub["x"],y=sub["y"],mode="markers",
            marker=dict(size=sizes,color=color,opacity=.34,line=dict(color=color,width=1.4)),
            text=text,hovertemplate="%{text}<extra></extra>",showlegend=False,name="",
        ))
    return _finish_map(fig,geojson,height)

def turnout_map_panel(geojson, summary, height=420):
    d = summary.merge(label_lookup(geojson), on="municipality_code", how="inner")
    fig = go.Figure()
    for f in geojson["features"]:
        x,y = _geometry_xy(f["geometry"])
        fig.add_trace(go.Scatter(x=x,y=y,mode="lines",line=dict(color="#D4D4D4",width=.7),hoverinfo="skip",showlegend=False,name=""))
    avail = d[d["turnout_rate"].notna()].copy()
    if not avail.empty:
        minv,maxv = float(avail["turnout_rate"].min()),float(avail["turnout_rate"].max())
        span=max(maxv-minv,1e-6)
        sizes = 14 + 34*((avail["turnout_rate"]-minv)/span)
        text = (
            "<b>"+avail["municipality_name"]+"</b>"
            + "<br><span style='color:#777'>投票率</span>"
            + "<br><b>"+avail["turnout_rate"].map(lambda x:f"{100*x:.1f}%")+"</b>"
        )
        fig.add_trace(go.Scatter(
            x=avail["x"],y=avail["y"],mode="markers",
            marker=dict(size=sizes,color="#777777",opacity=.28,line=dict(color="#666666",width=1.2)),
            text=text,hovertemplate="%{text}<extra></extra>",showlegend=False,name="",
        ))
    return _finish_map(fig,geojson,height)

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

def two_bloc_margin(results,election_id):
    d=results[results["election_id"]==election_id].copy()
    d["bloc"]=d["attribute"].map(
        lambda x: "保守系" if x=="保守系" else ("青陣営" if x in BLUE_BLOC_ATTRS else None)
    )
    bloc=d[d["bloc"].notna()]
    sums=(
        bloc.groupby(["municipality_code","bloc"],as_index=False)["votes"].sum()
        .pivot(index="municipality_code",columns="bloc",values="votes")
        .fillna(0).reset_index()
    )
    valid=d.groupby("municipality_code",as_index=False)["valid_votes"].first()
    for c in ["保守系","青陣営"]:
        if c not in sums.columns:
            sums[c]=0.0
    sums=sums.merge(valid,on="municipality_code",how="left")
    sums["margin"]=100*(sums["保守系"]-sums["青陣営"])/sums["valid_votes"].replace(0,pd.NA)
    return sums[["municipality_code","margin"]].fillna(0)

def state_margin(results,election_id):
    d=results[results["election_id"]==election_id].copy()
    cons=d.loc[d["attribute"]=="保守系","votes"].sum()
    blue=d.loc[d["attribute"].isin(BLUE_BLOC_ATTRS),"votes"].sum()
    allv=d["votes"].sum()
    return 0.0 if allv==0 else 100*(cons-blue)/allv

def shift_map_panel(geojson,swing,global_max_shift,height=420):
    loc=label_lookup(geojson)
    codes={str(f["properties"]["municipality_code"]) for f in geojson["features"]}
    s=swing[swing["municipality_code"].isin(codes)].copy().merge(loc,on="municipality_code",how="left")
    fig=go.Figure()
    for f in geojson["features"]:
        x,y=_geometry_xy(f["geometry"])
        fig.add_trace(go.Scatter(x=x,y=y,mode="lines",line=dict(color="#D7D7D7",width=.75),hoverinfo="skip",showlegend=False,name=""))
    for direction,color,symbol,positive in [("保守",RED,"triangle-right",True),("革新・オール沖縄",BLUE,"triangle-left",False)]:
        lx=[];ly=[];mx=[];my=[];ms=[];text=[]
        part=s[s["shift"]>0] if positive else s[s["shift"]<0]
        for _,r in part.iterrows():
            sh=abs(float(r["shift"]))
            if sh<.05:
                continue
            x=float(r["x"]);y=float(r["y"])
            length=.8+6.2*min(sh/max(global_max_shift,1),1)
            tail,head=(x-length,x+length*.2) if positive else (x+length,x-length*.2)
            lx += [tail,head,None];ly += [y,y,None]
            mx.append(head);my.append(y);ms.append(7+10*min(sh/max(global_max_shift,1),1))
            text.append(f"<b>{r['municipality_name']}</b><br>{direction}方向へ {sh:.1f}pt")
        if lx:
            fig.add_trace(go.Scatter(x=lx,y=ly,mode="lines",line=dict(color=color,width=2.2),hoverinfo="skip",showlegend=False,name=""))
            fig.add_trace(go.Scatter(
                x=mx,y=my,mode="markers",
                marker=dict(symbol=symbol,size=ms,color=color,line=dict(color=color,width=1)),
                text=text,hovertemplate="%{text}<extra></extra>",showlegend=False,name="",
            ))
    zeros=s[s["shift"].abs()<.05]
    if not zeros.empty:
        fig.add_trace(go.Scatter(
            x=zeros["x"],y=zeros["y"],mode="markers",
            marker=dict(size=9,color=GRAY,line=dict(color=GRAY,width=1)),
            text="<b>"+zeros["municipality_name"]+"</b><br>変化なし",
            hovertemplate="%{text}<extra></extra>",showlegend=False,name="",
        ))
    return _finish_map(fig,geojson,height)

def render_candidate_totals(totals):
    html=[]
    for _,r in totals.iterrows():
        color=candidate_color(r["attribute"])
        html.append(f"""
        <div class="result-card" style="border-left:7px solid {color};padding-left:12px;">
          <div style="display:grid;grid-template-columns:1.5fr .8fr .65fr;gap:10px;align-items:end;">
            <div><span class="candidate-name">{r['candidate_name']}</span>{attribute_badge(r['attribute'])}<br><span class="candidate-party">{r['party'] or r['attribute']}</span></div>
            <div class="big-num">{float(r['votes']):,.0f}</div>
            <div class="pct-num">{float(r['pct']):.2f}%</div>
          </div>
          <div class="progress-outer"><div class="progress-inner" style="width:{min(float(r['pct']),100):.2f}%;background:{color};"></div></div>
        </div>
        """)
    return "\n".join(html)

# ---------------- data ----------------
results,elections,turnout,municipalities,geojson,layout_boxes=load_all()
elections=elections.sort_values("date_serial",ascending=False).copy()
elections["short_label"]=elections.apply(short_label,axis=1)
elections["full_label"]=elections.apply(full_label,axis=1)

# ---------------- header / selectors ----------------
st.markdown('<div class="page-kicker">OKINAWA ELECTION ARCHIVE</div>',unsafe_allow_html=True)
st.markdown('<div class="page-title">過去の選挙結果</div>',unsafe_allow_html=True)
st.markdown('<div class="deck">全県選挙の確定結果を、市町村地図・票差・投票率・保革マージンで比較します。</div>',unsafe_allow_html=True)
st.markdown('<div class="top-rule"></div>',unsafe_allow_html=True)

sel_col,info_col=st.columns([1.0,1.65],gap="large")
with sel_col:
    selected_label=st.selectbox("表示する選挙",elections["short_label"].tolist(),index=0)
    selected_id=elections.loc[elections["short_label"]==selected_label,"election_id"].iloc[0]
with info_col:
    selected_meta=elections[elections["election_id"]==selected_id].iloc[0]
    st.markdown(f"**{selected_meta['full_label']}**")
    st.caption("選択すると、候補者集計・地図・市町村一覧がすべて切り替わります。")

d,summary,totals,state_tie=election_snapshot(results,selected_id,municipalities,turnout)

winner_name="同数" if state_tie else totals.iloc[0]["candidate_name"]
winner_color=GRAY if state_tie else candidate_color(totals.iloc[0]["attribute"])
state_valid=float(d.groupby("municipality_code")["valid_votes"].first().sum())

st.markdown(
    f"""
<div style="background:{winner_color};color:#fff;padding:16px 19px;margin-top:8px;">
  <div style="font-size:.82rem;font-weight:800;letter-spacing:.06em;">確定結果</div>
  <div style="font-family:Georgia,'Yu Mincho',serif;font-size:1.65rem;font-weight:800;margin-top:2px;">{winner_name}</div>
</div>
<div class="stat-strip">
  <span>有効投票 <strong>{state_valid:,.0f}票</strong></span>
  <span>候補者数 <strong>{len(totals)}</strong></span>
  <span>市町村 <strong>{summary['municipality_code'].nunique()}</strong></span>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------- top result + map ----------------
left,right=st.columns([1.05,1.15],gap="large")
with left:
    st.markdown('<div class="eyebrow">全県集計</div>',unsafe_allow_html=True)
    st.markdown(render_candidate_totals(totals),unsafe_allow_html=True)
with right:
    st.markdown('<div class="eyebrow">市町村別マップ</div>',unsafe_allow_html=True)
    modes=["得票シェア","リード票"]
    has_turnout=summary["turnout_rate"].notna().any()
    if has_turnout:
        modes.append("投票率")
    map_mode=st.radio("表示",modes,horizontal=True,label_visibility="collapsed")
    global_max_lead=max(float(summary["lead_votes"].max()),1.0)
    if map_mode=="得票シェア":
        render_boxed_map(winner_map_panel,geojson,layout_boxes,600,"hist-share",summary,d)
        st.caption("本島を中央、周辺離島を外周の枠へ配置した模式図。濃い赤・濃い青ほど勝者のリード幅が大きく、同数はグレー。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。")
    elif map_mode=="リード票":
        render_boxed_map(lead_bubble_panel,geojson,layout_boxes,510,"hist-lead",summary,global_max_lead=global_max_lead)
        st.caption("円の大きさ＝1位と2位の票差。本島・離島で同じサイズ基準。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。")
    else:
        render_boxed_map(turnout_map_panel,geojson,layout_boxes,510,"hist-turnout",summary)
        st.caption("投票率データがDBにある選挙のみ表示します。1本指で移動。地図の上にあるスライダーで拡大・縮小できます。")

# ---------------- municipality table ----------------
st.markdown('<div class="section-title">市町村別結果</div>',unsafe_allow_html=True)
st.markdown('<div class="section-deck">オール沖縄・革新が優位な市町村から保守が優位な市町村の順に並びます(列見出しで並べ替えも可能)。</div>',unsafe_allow_html=True)

table=summary.copy()
table["勝者"]=table.apply(lambda r:"同数" if r["leader_attribute"]=="同数" else r["leader_name"],axis=1)
table["リードpt"]=table["lead_points"]
table["リード票"]=table["lead_votes"]
table["有効投票"]=table["valid_votes"]
table["投票率"]=table["turnout_rate"].map(lambda x:None if pd.isna(x) else 100*x)
_margin=two_bloc_margin(results,selected_id).rename(columns={"margin":"_sort_margin"})
table=table.merge(_margin,on="municipality_code",how="left").sort_values("_sort_margin",ascending=True)
show_cols=["municipality_name","勝者","リードpt","リード票","有効投票"]
if has_turnout:
    show_cols.append("投票率")
table=table[show_cols].rename(columns={"municipality_name":"市町村"})

config={
    "リードpt":st.column_config.NumberColumn(format="%.1f"),
    "リード票":st.column_config.NumberColumn(format="%.0f"),
    "有効投票":st.column_config.NumberColumn(format="%.0f"),
}
if has_turnout:
    config["投票率"]=st.column_config.NumberColumn(format="%.1f%%")
st.dataframe(table,hide_index=True,use_container_width=True,height=540,column_config=config)

# ---------------- comparison ----------------
st.markdown('<div class="section-title">保革マージンを別の選挙と比較</div>',unsafe_allow_html=True)
st.markdown('<div class="section-deck">比較対象は表示中の選挙とは独立して選べます。赤＝保守方向、青＝革新・オール沖縄方向、変化なし＝グレー。</div>',unsafe_allow_html=True)

compare_candidates=elections[elections["election_id"]!=selected_id].copy()
# Default: immediately older election, otherwise first available.
selected_date=float(selected_meta["date_serial"])
older=compare_candidates[compare_candidates["date_serial"]<selected_date].sort_values("date_serial",ascending=False)
default_compare_id=older.iloc[0]["election_id"] if not older.empty else compare_candidates.iloc[0]["election_id"]
default_compare_label=compare_candidates.loc[compare_candidates["election_id"]==default_compare_id,"short_label"].iloc[0]
compare_labels=compare_candidates["short_label"].tolist()
default_index=compare_labels.index(default_compare_label)
compare_label=st.selectbox("比較対象の選挙",compare_labels,index=default_index)
compare_id=compare_candidates.loc[compare_candidates["short_label"]==compare_label,"election_id"].iloc[0]

a=two_bloc_margin(results,selected_id).rename(columns={"margin":"selected_margin"})
b=two_bloc_margin(results,compare_id).rename(columns={"margin":"compare_margin"})
swing=(
    summary[["municipality_code","municipality_name"]]
    .merge(a,on="municipality_code",how="left")
    .merge(b,on="municipality_code",how="left")
)
swing["shift"]=swing["selected_margin"]-swing["compare_margin"]
global_max_shift=max(float(swing["shift"].abs().max()),1.0)

state_shift=state_margin(results,selected_id)-state_margin(results,compare_id)
direction="保守" if state_shift>0 else "オール沖縄" if state_shift<0 else "変化なし"
direction_color=RED if state_shift>0 else BLUE if state_shift<0 else GRAY

st.markdown(
    f'<div style="font-size:1.15rem;font-weight:800;color:{direction_color};margin:.2rem 0 .6rem;">'
    f'{compare_label} → {selected_label}：県全体 {direction}{"へ " + format(abs(state_shift), ".1f") + "pt" if state_shift else ""}</div>',
    unsafe_allow_html=True,
)

comp_left,comp_right=st.columns([1.1,1.0],gap="large")
with comp_left:
    render_boxed_map(shift_map_panel,geojson,layout_boxes,510,"history-shift",swing,global_max_shift)
    st.markdown(
        f'<div class="legend-row"><span style="color:{RED};font-weight:800;">→ 保守方向</span>'
        f'<span style="color:{BLUE};font-weight:800;">← 革新・オール沖縄方向</span>'
        f'<span style="color:{GRAY};font-weight:800;">● 変化なし</span></div>',
        unsafe_allow_html=True,
    )
with comp_right:
    comp=swing.copy()
    comp["表示選挙マージン"]=comp["selected_margin"].map(lambda x:f"保守 +{x:.1f}" if x>0 else f"革新・オール沖縄 +{abs(x):.1f}" if x<0 else "同率")
    comp["比較選挙マージン"]=comp["compare_margin"].map(lambda x:f"保守 +{x:.1f}" if x>0 else f"革新・オール沖縄 +{abs(x):.1f}" if x<0 else "同率")
    comp["シフト"]=comp["shift"]
    comp=comp.sort_values("シフト",key=lambda s:s.abs(),ascending=False)
    st.dataframe(
        comp[["municipality_name","表示選挙マージン","比較選挙マージン","シフト"]].rename(columns={"municipality_name":"市町村"}),
        hide_index=True,use_container_width=True,height=520,
        column_config={"シフト":st.column_config.NumberColumn(format="%+.1f pt")},
    )

st.markdown(
    '<div class="note-box"><b>比較の定義：</b> 各選挙で「保守系得票率－（革新系［2014年以前］＋オール沖縄系）得票率」を算出し、'
    '表示中の選挙から比較対象の選挙を差し引きます。第三候補・その他候補の票も全有効票の分母に残します。</div>',
    unsafe_allow_html=True,
)
