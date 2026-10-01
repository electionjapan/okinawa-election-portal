"""
2026年米国中間選挙(2026-11-03) ポータル（沖縄選挙ポータル内の新ページ）

データソースは civicAPI (https://civicapi.org) の無料・認証不要API。
公式選管・AP通信等の公式コール(当確)ではない非公式のサードパーティAPIであるため、
全ページで「参考情報」であることを明示する。

構成:
  1. 開票速報  … 上院・知事選の州別現在値を一覧表示
  2. 全米マップ … 上院 / 知事選を選んで、リード政党で塗り分けた全米地図
  3. 注目レース一覧 … 下院の代表的な接戦区ウォッチリスト(編集可能な初期セット)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import us_midterm_data as umd

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

APP_DIR = Path(__file__).resolve().parent

DEM_COLOR = "#1675B9"
REP_COLOR = "#C93238"
OTHER_COLOR = "#8E8E8E"
NODATA_COLOR = "#E7E7E7"


def party_color(party: str | None) -> str:
    if not party:
        return OTHER_COLOR
    p = party.strip().lower()
    if p.startswith("dem"):
        return DEM_COLOR
    if p.startswith("rep") or p.startswith("gop"):
        return REP_COLOR
    return OTHER_COLOR


def party_label_ja(party: str | None) -> str:
    if not party:
        return "不明"
    p = party.strip().lower()
    if p.startswith("dem"):
        return "民主党"
    if p.startswith("rep") or p.startswith("gop"):
        return "共和党"
    return party


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
@media(max-width:800px){
  .block-container{padding-left:.7rem;padding-right:.7rem;padding-top:.6rem !important;}
}
.um-badge {
    display:inline-block;
    font-size:.72rem;
    font-weight:800;
    letter-spacing:.06em;
    padding:.15rem .5rem;
    border-radius:3px;
    color:#fff;
}
.um-card {
    border:1px solid #DDD;
    border-left:5px solid #AAA;
    padding:.75rem .9rem;
    margin-bottom:.55rem;
    background:#fff;
}
.um-card-title { font-weight:800; font-size:1.02rem; margin-bottom:.25rem; }
.um-card-row { display:flex; justify-content:space-between; font-size:.9rem; padding:.1rem 0; }
.um-disclaimer {
    background:#FFF7E6;
    border:1px solid #F0D79A;
    padding:.6rem .85rem;
    font-size:.82rem;
    color:#6B5312;
    line-height:1.6;
    margin-bottom:1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_usmidterm", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 2026年米国中間選挙</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)

st.markdown("## 2026年米国中間選挙(2026年11月3日)")
st.markdown(
    '<div class="um-disclaimer">'
    "データは非公式・無料のサードパーティAPI「civicAPI」から取得しています。"
    "州選管や連邦議会、AP通信などによる公式の確定結果・当確(コール)ではないため、"
    "参考情報としてご利用ください。開票率0%の州は投票開始前のプレースホルダーです。"
    "</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 2026年米国中間選挙")
    if st.button("↻ 最新の状態を再取得", key="refresh_usmidterm", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    autorefresh_on = st.checkbox(
        "自動更新を有効にする（選挙当日向け）",
        value=False,
        help="オンにすると30秒ごとにcivicAPIへ再アクセスします。選挙期間外は手動更新を推奨します。",
    )
    st.caption("civicAPI（非公式）を利用しています。公式の確定結果ではありません。")

if autorefresh_on and st_autorefresh is not None:
    st_autorefresh(interval=30 * 1000, limit=None, key="usmidterm-autorefresh")


@st.cache_data(ttl=300, show_spinner=False)
def _load_states_config():
    return umd.load_states_config()


@st.cache_data(ttl=300, show_spinner=False)
def _load_house_watchlist():
    return umd.load_house_watchlist()


@st.cache_data(ttl=300, show_spinner=False)
def _load_senate(states_key: str):
    states = _load_states_config()
    return umd.get_senate_races(states)


@st.cache_data(ttl=300, show_spinner=False)
def _load_governor(states_key: str):
    states = _load_states_config()
    return umd.get_governor_races(states)


@st.cache_data(ttl=300, show_spinner=False)
def _load_house_watchlist_races(watchlist_key: str):
    watchlist = _load_house_watchlist()
    return umd.get_house_watchlist_races(watchlist)


fetch_errors: list[str] = []

try:
    senate_races, senate_errors = _load_senate("v1")
    st.session_state["usmidterm_senate_cache"] = senate_races
except Exception as exc:  # noqa: BLE001
    senate_races = st.session_state.get("usmidterm_senate_cache", {})
    fetch_errors.append(f"上院データ取得エラー: {exc}")
    senate_errors = []

try:
    governor_races, governor_errors = _load_governor("v1")
    st.session_state["usmidterm_governor_cache"] = governor_races
except Exception as exc:  # noqa: BLE001
    governor_races = st.session_state.get("usmidterm_governor_cache", {})
    fetch_errors.append(f"知事選データ取得エラー: {exc}")
    governor_errors = []

try:
    house_races, house_errors = _load_house_watchlist_races("v1")
    st.session_state["usmidterm_house_cache"] = house_races
except Exception as exc:  # noqa: BLE001
    house_races = st.session_state.get("usmidterm_house_cache", {})
    fetch_errors.append(f"下院データ取得エラー: {exc}")
    house_errors = []

if not senate_races and not governor_races and not house_races:
    st.error("civicAPIからデータを取得できませんでした。しばらくしてから「↻ 最新の状態を再取得」をお試しください。")
    for e in fetch_errors:
        st.caption(e)
    st.stop()

if fetch_errors or senate_errors or governor_errors or house_errors:
    with st.expander("一部のデータ取得に失敗しています（クリックで詳細）", expanded=False):
        for e in fetch_errors + senate_errors + governor_errors + house_errors:
            st.caption(e)

tab_live, tab_map, tab_watch = st.tabs(["開票速報", "全米マップ", "注目レース一覧"])


def _race_rows(races: dict) -> pd.DataFrame:
    rows = []
    for code, race in races.items():
        candidates = sorted(race.get("candidates") or [], key=lambda c: c.get("votes") or 0, reverse=True)
        lead = candidates[0] if candidates else None
        runner = candidates[1] if len(candidates) > 1 else None
        rows.append({
            "州": code,
            "開票率": race.get("percent_reporting") or 0,
            "首位候補": lead.get("name") if lead else "—",
            "首位政党": party_label_ja(lead.get("party")) if lead else "—",
            "首位得票率": lead.get("percent") if lead else None,
            "次点候補": runner.get("name") if runner else "—",
            "次点得票率": runner.get("percent") if runner else None,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("州").reset_index(drop=True)
    return df


with tab_live:
    st.markdown("### 上院(Senate)")
    if senate_races:
        df_sen = _race_rows(senate_races)
        st.dataframe(df_sen, use_container_width=True, hide_index=True)
    else:
        st.info("上院の州別データをまだ取得できていません。")

    st.markdown("### 知事選(Governor)")
    if governor_races:
        df_gov = _race_rows(governor_races)
        st.dataframe(df_gov, use_container_width=True, hide_index=True)
    else:
        st.info("知事選の州別データをまだ取得できていません。")


def _build_choropleth(races: dict, title: str):
    locations, z, hover = [], [], []
    for code, race in races.items():
        lead_party = umd.leading_party(race)
        candidates = sorted(race.get("candidates") or [], key=lambda c: c.get("votes") or 0, reverse=True)
        lead = candidates[0] if candidates else None
        if lead_party and lead_party.strip().lower().startswith("dem"):
            val = -1
        elif lead_party and (lead_party.strip().lower().startswith("rep") or lead_party.strip().lower().startswith("gop")):
            val = 1
        else:
            val = 0
        locations.append(code)
        z.append(val)
        pct = race.get("percent_reporting") or 0
        if lead is None:
            hover.append(f"{code}<br>データなし")
        else:
            hover.append(
                f"{code}<br>{lead.get('name','')}（{party_label_ja(lead.get('party'))}）"
                f"<br>得票率 {(lead.get('percent') or 0):.1f}%　開票率 {pct:.0f}%"
            )

    fig = go.Figure(
        go.Choropleth(
            locations=locations,
            z=z,
            locationmode="USA-states",
            text=hover,
            hovertemplate="%{text}<extra></extra>",
            colorscale=[[0, DEM_COLOR], [0.5, "#F2F2F2"], [1, REP_COLOR]],
            zmin=-1,
            zmax=1,
            showscale=False,
            marker_line_color="white",
            marker_line_width=1,
        )
    )
    fig.update_layout(
        title=title,
        geo=dict(scope="usa", projection=dict(type="albers usa"), showlakes=False),
        margin=dict(l=0, r=0, t=40, b=0),
        height=520,
    )
    return fig


with tab_map:
    map_target = st.radio("表示するレース", ["上院(Senate)", "知事選(Governor)"], horizontal=True)
    races_for_map = senate_races if map_target.startswith("上院") else governor_races
    if races_for_map:
        st.plotly_chart(_build_choropleth(races_for_map, map_target), use_container_width=True)
        st.caption("青＝民主党がリード／赤＝共和党がリード／グレー＝データなし・接戦不明・その他政党。開票率0%の州はまだ投票前です。")
    else:
        st.info("地図に表示できるデータがまだありません。")


with tab_watch:
    st.markdown("### 下院(House) 注目レース一覧")
    st.caption(
        "過去の選挙サイクルで接戦が続いてきた代表的な選挙区をいくつか選んだ初期ウォッチリストです。"
        "435選挙区すべてを網羅するものではなく、『当選確実』『優勢』等の予測ラベルも付けていません。"
        "data/us_house_watchlist_2026.json を編集すると表示対象を増減できます。"
    )
    watchlist = _load_house_watchlist()
    cols = st.columns(2)
    for i, entry in enumerate(watchlist):
        district = entry["district"]
        race = house_races.get(district)
        with cols[i % 2]:
            if race is None:
                st.markdown(
                    f'<div class="um-card"><div class="um-card-title">{district}（{entry["state"]}）</div>'
                    '<div class="um-card-row">データ未取得</div></div>',
                    unsafe_allow_html=True,
                )
                continue
            candidates = sorted(race.get("candidates") or [], key=lambda c: c.get("votes") or 0, reverse=True)
            pct = race.get("percent_reporting") or 0
            status = "開票前" if pct == 0 else f"開票率 {pct:.0f}%"
            rows_html = ""
            for c in candidates:
                color = party_color(c.get("party"))
                votes = c.get("votes") or 0
                vpct = c.get("percent") or 0
                rows_html += (
                    f'<div class="um-card-row">'
                    f'<span><span class="um-badge" style="background:{color}">{party_label_ja(c.get("party"))}</span> '
                    f'{c.get("name","")}</span>'
                    f'<span>{votes:,}票（{vpct:.1f}%）</span></div>'
                )
            st.markdown(
                f'<div class="um-card">'
                f'<div class="um-card-title">{district}（{entry["state"]}）　'
                f'<span style="color:#888;font-weight:400;font-size:.8rem;">{status}</span></div>'
                f'{rows_html}</div>',
                unsafe_allow_html=True,
            )

st.caption("v0.9.39 · US MIDTERMS 2026 · civicAPI（非公式）")
