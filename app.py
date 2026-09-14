from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from live_data import GOOGLE_SHEET_ID, build_live_models, load_google_workbook
from map_view import BLUE, RED, ZOOM_PRESETS, build_map_figure

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(
    page_title="沖縄県知事選 開票マップ【実寸版】",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
html, body, [class*="css"] { font-family: Meiryo, "Yu Gothic", sans-serif; }
.block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1500px; }
.real-title { font-size: 2.05rem; font-weight: 800; letter-spacing: .02em; color:#202124; }
.real-sub { color:#666; margin:.25rem 0 1.2rem; font-size:1rem; }
.live-pill { display:inline-block; background:#c93238; color:white; font-weight:700; padding:.18rem .55rem; border-radius:999px; margin-right:.45rem; }
.note-box { background:#f7f7f7; border-left:4px solid #8e8e8e; padding:.65rem .85rem; font-size:.88rem; color:#555; margin-top:.6rem; }
.candidate-card { border:1px solid #e0e0e0; border-radius:10px; padding:.65rem .75rem; background:white; min-height:104px; }
.candidate-name { font-size:1rem; font-weight:700; }
.candidate-votes { font-size:1.35rem; font-weight:800; margin-top:.18rem; }
.candidate-pct { color:#666; font-size:.88rem; }
</style>
""",
    unsafe_allow_html=True,
)


def load_json(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=12, show_spinner=False)
def get_live_book(sheet_id: str):
    return load_google_workbook(sheet_id)


@st.cache_data(show_spinner=False)
def load_static():
    municipalities = pd.DataFrame(load_json("municipalities.json"))
    invalid_history = pd.DataFrame(load_json("invalid_history_v1.json"))
    results = pd.DataFrame(load_json("statewide_results.json"))
    geojson = load_json("okinawa_municipalities_real_distance_approx_v2.geojson")
    return municipalities, invalid_history, results, geojson


def build_prev_context(results: pd.DataFrame, election_id: str = "GOV2022"):
    d = results[results["election_id"] == election_id].copy()
    out = {}
    for code, grp in d.groupby("municipality_code"):
        grp = grp.sort_values("votes", ascending=False)
        if grp.empty:
            continue
        top = grp.iloc[0]
        second_votes = float(grp.iloc[1]["votes"]) if len(grp) > 1 else 0.0
        valid = float(top.get("valid_votes", 0) or 0)
        point_diff = 100 * (float(top["votes"]) - second_votes) / valid if valid > 0 else 0.0
        out[str(code)] = {
            "winner_name": top["candidate_name"],
            "winner_attribute": top["attribute"],
            "point_diff": point_diff,
        }
    return out


municipalities, invalid_history, historical_results, geojson = load_static()
prev_context = build_prev_context(historical_results)

if st_autorefresh is not None:
    st_autorefresh(interval=15_000, limit=None, key="real-map-refresh")

with st.sidebar:
    st.markdown("### 表示設定")
    mode = st.radio("地図モード", ["得票シェア", "国盗り", "リード票", "残票"], index=0)
    zoom_preset = st.selectbox("クイックズーム", list(ZOOM_PRESETS.keys()), index=0)
    show_labels = st.checkbox("市町村名を表示", value=False)
    if st.button("↻ 最新の状態を再取得", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("15秒ごとにGoogleスプレッドシートを再取得します。")
    st.caption("島を移動・拡大せず、本来の位置関係に近い配置で表示します。")

try:
    live_book = get_live_book(GOOGLE_SHEET_ID)
    st.session_state["realmap_last_good_book"] = live_book
    st.session_state["realmap_last_error"] = ""
except Exception as exc:
    st.session_state["realmap_last_error"] = str(exc)
    live_book = st.session_state.get("realmap_last_good_book")

if live_book is None:
    st.error("速報データを取得できません。Googleスプレッドシートの共有設定または通信状態を確認してください。")
    if st.session_state.get("realmap_last_error"):
        st.caption(st.session_state["realmap_last_error"])
    st.stop()

try:
    models = build_live_models(live_book, municipalities, invalid_history=invalid_history)
except Exception as exc:
    st.error(f"速報データを読み取れませんでした: {exc}")
    st.stop()

if st.session_state.get("realmap_last_error"):
    st.warning("直近のデータ取得に失敗したため、最後に正常取得できたデータを表示しています。")

current = models.current
msum = models.msum
totals = models.totals

st.markdown('<span class="live-pill">LIVE</span><span class="real-title">沖縄県知事選 開票マップ【実寸版】</span>', unsafe_allow_html=True)
st.markdown(
    '<div class="real-sub">沖縄本島・宮古・八重山・大東など、島々の実際の位置関係に近い形で表示しています。</div>',
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("全県開票率", "—" if models.overall_reporting is None else f"{models.overall_reporting:.1f}%")
m2.metric("開票確定自治体", f"{models.confirmed_count}/41")
m3.metric("投票速報", models.turnout_label or "未入力")
m4.metric("最終更新", models.latest_update)

# Candidate total cards: top six in vote order.
cards = st.columns(3)
for i, (_, row) in enumerate(totals.head(6).iterrows()):
    attr = str(row.get("attribute", ""))
    accent = RED if attr == "保守系" else (BLUE if attr in {"オール沖縄系", "革新系（2014年以前）"} else "#8E8E8E")
    cards[i % 3].markdown(
        f"""
<div class="candidate-card" style="border-top:4px solid {accent};">
  <div class="candidate-name">{row['candidate_name']}</div>
  <div class="candidate-votes">{int(row['current_votes']):,}票</div>
  <div class="candidate-pct">県計得票構成比 {float(row['pct']):.1f}%</div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("### 実寸開票マップ")
fig = build_map_figure(
    geojson=geojson,
    msum=msum,
    current=current,
    mode=mode,
    zoom_preset=zoom_preset,
    show_labels=show_labels,
    prev_context=prev_context,
    height=700,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})

if mode == "得票シェア":
    st.caption("得票シェア：首位陣営の色を、1位と2位のポイント差に応じて濃淡表示します。25ポイント差で最大濃度です。")
elif mode == "国盗り":
    st.caption("国盗り：勝差にかかわらず、保守系首位＝赤、オール沖縄系首位＝青。同数・その他・未開票はグレー系です。")
elif mode == "リード票":
    st.caption("リード票：円の大きさが1位と2位の票差を表します。")
else:
    st.caption("残票：円の大きさが残票数を表します。開票確定自治体は残票0として表示しません。")

st.markdown(
    '<div class="note-box">※市町村境界はWeb表示用に簡略化しています。島々の位置関係・距離感を重視した表示です。厳密な測量・行政境界確認用途には使用しないでください。</div>',
    unsafe_allow_html=True,
)
