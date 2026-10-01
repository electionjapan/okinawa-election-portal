"""
2026年米国中間選挙(2026年11月3日) ポータル（沖縄選挙ポータル内の新ページ）

「Election Night Dashboard」として全面改修したバージョン(v0.9.40)。
データソースは civicAPI (https://civicapi.org) の無料・認証不要API。
公式選管・AP通信等の公式コール(当確)ではない非公式のサードパーティAPIであるため、
全ページで「参考情報」であることを明示する。

画面構成(上から下):
  1. Election Header（LIVE/PREVIEW/RESULTSバッジ、最終更新時刻）
  2. Data / Update Status Strip
  3. BALANCE OF POWER（上院・下院の勢力バー）
  4. LIVE WATCH STRIP（接戦上院レースの横長サマリー）
  5. WATCH DESK（登録レースのカードグリッド、カテゴリ・州フィルター付き）
  6. U.S. MAP（上院／知事選を切り替えられる全米地図）
  7. ALL RACES（表形式の補助ビュー、expander内）
  8. データソース・免責事項
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import us_midterm_data as umd

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

APP_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# カラートークン
# ---------------------------------------------------------------------------
BG = "#F7F7F5"
CARD = "#FFFFFF"
TEXT = "#171717"
SUBTEXT = "#6B7280"
BORDER = "#D9DDE3"
DEM = "#2468B4"
REP = "#C63C45"
OTHER = "#777777"
NODATA = "#E8EAED"

DEM_CALL = "#2468B4"
DEM_LEAD = "#A9C7E8"
REP_CALL = "#C63C45"
REP_LEAD = "#E7ACB1"

STATUS_LABEL_JA = {
    "called": "当確",
    "leading": "リード",
    "not_reporting": "開票前",
    "no_data": "データなし",
}


def accent_color(race: dict) -> str:
    status = umd.race_status(race)
    bucket = umd.party_bucket(umd.leading_party(race))
    if status == "called" and bucket == "dem":
        return DEM_CALL
    if status == "called" and bucket == "rep":
        return REP_CALL
    if status == "leading" and bucket == "dem":
        return DEM_LEAD
    if status == "leading" and bucket == "rep":
        return REP_LEAD
    return NODATA


def party_label_ja(party: str | None) -> str:
    bucket = umd.party_bucket(party)
    if bucket == "dem":
        return "民主党"
    if bucket == "rep":
        return "共和党"
    return party or "不明"


# ---------------------------------------------------------------------------
# スタイル
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
html, body, [class*="css"] {{ font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:{TEXT}; }}
.block-container {{ max-width:1420px; padding-top:.6rem; padding-bottom:4rem; background:{BG}; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ display:none !important; }}
div[data-testid="stAppViewContainer"] {{ padding-top:0 !important; background:{BG}; }}
.portal-nav-spacer {{ height:.15rem; }}
.portal-breadcrumb {{ color:{SUBTEXT}; font-size:.82rem; padding-top:.68rem; white-space:nowrap; }}

* {{ font-variant-numeric: tabular-nums; }}

.en-preview-banner {{
  background:#FFF4D6; border:1.5px solid #E8B93B; color:#6B4E04; font-weight:800;
  text-align:center; padding:.5rem; font-size:.85rem; letter-spacing:.03em; margin-bottom:.6rem;
}}

.en-header {{ padding:.6rem 0 .3rem; }}
.en-header-top {{ display:flex; align-items:center; gap:.4rem; }}
.en-live-dot {{ width:9px; height:9px; border-radius:50%; background:{OTHER}; }}
.en-live-dot.on {{ background:#D32C3C; animation:en-pulse 1.4s infinite; }}
@keyframes en-pulse {{ 0%{{opacity:1;}} 50%{{opacity:.25;}} 100%{{opacity:1;}} }}
.en-live-label {{ font-weight:800; font-size:.78rem; letter-spacing:.09em; color:{SUBTEXT}; }}
.en-header-title {{
  font-family:Georgia,"Yu Mincho",serif; font-weight:800; font-size:2.35rem; letter-spacing:-.02em;
  margin-top:.1rem; color:{TEXT};
}}
.en-header-sub {{ font-weight:700; font-size:.92rem; color:{SUBTEXT}; letter-spacing:.03em; margin-top:.1rem; }}
.en-header-updated {{ font-size:.78rem; color:{SUBTEXT}; margin-top:.3rem; }}

.en-status-strip {{
  border-top:1px solid {BORDER}; border-bottom:1px solid {BORDER};
  padding:.4rem .1rem; font-size:.78rem; color:{SUBTEXT}; margin:.5rem 0 1.1rem;
  display:flex; justify-content:space-between; flex-wrap:wrap; gap:.4rem;
}}

.en-controls {{ display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; margin:.3rem 0 .9rem; }}

.section-title {{
  font-family:Georgia,"Yu Mincho",serif; font-weight:800; font-size:1.3rem; color:{TEXT};
  margin:1.6rem 0 .5rem; letter-spacing:.01em;
}}

/* Balance of power */
.bop-block {{ background:{CARD}; border:1px solid {BORDER}; padding:1rem 1.2rem 1.1rem; margin-bottom:.9rem; }}
.bop-heading {{ font-weight:800; font-size:.85rem; letter-spacing:.08em; color:{SUBTEXT}; margin-bottom:.5rem; }}
.bop-row {{ display:flex; align-items:center; gap:.8rem; }}
.bop-label {{ font-size:.78rem; font-weight:800; color:{SUBTEXT}; letter-spacing:.03em; min-width:92px; }}
.bop-label .bop-num {{ display:block; font-size:1.5rem; color:{TEXT}; font-weight:800; margin-top:.1rem; }}
.bop-label-right {{ text-align:right; }}
.bop-bar-wrap {{ flex:1; position:relative; }}
.bop-bar {{ display:flex; height:26px; width:100%; border-radius:3px; overflow:hidden; background:{NODATA}; }}
.bop-seg {{ height:100%; }}
.bop-seg.dem {{ background:{DEM}; }}
.bop-seg.rep {{ background:{REP}; }}
.bop-seg.other {{ background:{OTHER}; }}
.bop-seg.uncalled {{ background:{NODATA}; }}
.bop-control-line {{
  position:absolute; top:-4px; bottom:-4px; width:0; border-left:2px dashed #555;
}}
.bop-control-line span {{
  position:absolute; top:-18px; left:50%; transform:translateX(-50%); font-size:.68rem;
  font-weight:800; color:#444; white-space:nowrap;
}}
.bop-note {{ text-align:center; font-size:.76rem; color:{SUBTEXT}; margin-top:.5rem; }}

.gov-stat-row {{ display:flex; gap:.7rem; flex-wrap:wrap; }}
.gov-stat-tile {{ flex:1; min-width:110px; background:{CARD}; border:1px solid {BORDER}; padding:.6rem .8rem; text-align:center; }}
.gov-stat-num {{ font-size:1.5rem; font-weight:800; }}
.gov-stat-label {{ font-size:.68rem; font-weight:800; letter-spacing:.07em; color:{SUBTEXT}; margin-top:.15rem; }}

/* Live watch strip */
.lws-wrap {{ overflow-x:auto; white-space:nowrap; background:{CARD}; border:1px solid {BORDER}; padding:.55rem .9rem; margin-bottom:1rem; }}
.lws-item {{ display:inline-block; font-size:.82rem; font-weight:700; margin-right:1rem; }}
.lws-sep {{ color:{BORDER}; margin-right:1rem; }}

/* Watch desk controls */
.pill-row {{ display:flex; gap:.4rem; flex-wrap:wrap; margin-bottom:.8rem; }}

/* Race card */
.race-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(330px, 1fr)); gap:.8rem; margin-bottom:1rem; }}
.race-card {{ background:{CARD}; border:1px solid {BORDER}; border-left:6px solid {NODATA}; padding:.8rem .95rem .75rem; }}
.race-card-top {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:.45rem; }}
.race-card-title {{ font-weight:800; font-size:.92rem; }}
.race-card-pct {{ font-size:.72rem; font-weight:800; color:{SUBTEXT}; white-space:nowrap; }}
.race-cand-row {{ display:flex; justify-content:space-between; align-items:center; font-size:.9rem; margin:.15rem 0; }}
.race-cand-name {{ font-weight:700; }}
.race-cand-pct {{ font-weight:800; font-size:1.02rem; }}
.race-cand-votes {{ font-size:.72rem; color:{SUBTEXT}; }}
.race-bar-wrap {{ position:relative; height:9px; background:{NODATA}; border-radius:2px; margin:.4rem 0 .5rem; overflow:hidden; }}
.race-bar-dem {{ position:absolute; left:0; top:0; bottom:0; background:{DEM}; }}
.race-bar-rep {{ position:absolute; right:0; top:0; bottom:0; background:{REP}; }}
.race-bar-mid {{ position:absolute; left:50%; top:-2px; bottom:-2px; width:1px; background:#fff; opacity:.8; }}
.race-margin {{ font-size:.8rem; font-weight:800; }}
.race-progress {{ height:4px; background:{NODATA}; border-radius:2px; overflow:hidden; margin-top:.5rem; }}
.race-progress-fill {{ height:100%; background:#9AA0A8; }}
.race-status-badge {{ font-size:.66rem; font-weight:800; letter-spacing:.05em; padding:.08rem .4rem; border-radius:2px; color:#fff; }}

.en-footer {{ color:{SUBTEXT}; font-size:.74rem; line-height:1.7; margin-top:1.5rem; border-top:1px solid {BORDER}; padding-top:.8rem; }}

@media(max-width:800px){{
  .block-container{{ padding-left:.7rem; padding-right:.7rem; padding-top:.6rem !important; }}
  .en-header-title{{ font-size:1.7rem; }}
  .race-grid{{ grid-template-columns:1fr; }}
  .bop-label{{ min-width:70px; font-size:.68rem; }}
  .bop-label .bop-num{{ font-size:1.15rem; }}
}}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ナビゲーション
# ---------------------------------------------------------------------------
nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_usmidterm", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 2026年米国中間選挙</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# コントロール（手動更新・自動更新・プレビューデータ・カテゴリ／州フィルターの一部）
# ---------------------------------------------------------------------------
ctl1, ctl2, ctl3, ctl4 = st.columns([1.1, 1.6, 1.6, 2.7])
with ctl1:
    if st.button("↻ 更新", key="refresh_usmidterm", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with ctl2:
    autorefresh_on = st.checkbox("自動更新 (30秒)", value=False, key="um_autorefresh")
with ctl3:
    preview_mode = st.checkbox("プレビュー用ダミーデータ", value=False, key="um_preview_mode")
with ctl4:
    st.caption("データ: civicAPI（非公式・参考情報） ／ 自動更新は選挙当日向け。詳細は下部の注記を参照。")

if autorefresh_on and st_autorefresh is not None and not preview_mode:
    st_autorefresh(interval=30 * 1000, limit=None, key="usmidterm-autorefresh")

if preview_mode:
    st.markdown(
        '<div class="en-preview-banner">⚠ DESIGN PREVIEW DATA ／ 実際の開票結果ではありません（ダミーデータ表示中）</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _load_states_config():
    return umd.load_states_config()


@st.cache_data(ttl=300, show_spinner=False)
def _load_house_watchlist():
    return umd.load_house_watchlist()


@st.cache_data(ttl=300, show_spinner=False)
def _load_holdover():
    return umd.load_holdover_config()


@st.cache_data(ttl=300, show_spinner=False)
def _load_senate(_states_key: str):
    return umd.get_senate_races(_load_states_config())


@st.cache_data(ttl=300, show_spinner=False)
def _load_governor(_states_key: str):
    return umd.get_governor_races(_load_states_config())


@st.cache_data(ttl=300, show_spinner=False)
def _load_house_watchlist_races(_watchlist_key: str):
    return umd.get_house_watchlist_races(_load_house_watchlist())


@st.cache_data(ttl=300, show_spinner=False)
def _load_all_house_races(_states_key: str):
    return umd.get_all_house_races(_load_states_config())


fetch_errors: list[str] = []
holdover = _load_holdover()
watchlist = _load_house_watchlist()

if preview_mode:
    senate_races, governor_races, house_races = umd.build_preview_data()
    all_house_races = house_races  # プレビュー時はBALANCE OF POWERもスペック例の固定値を使う
    senate_errors = governor_errors = house_errors = all_house_errors = []
else:
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
        fetch_errors.append(f"下院(注目レース)データ取得エラー: {exc}")
        house_errors = []

    try:
        all_house_races, all_house_errors = _load_all_house_races("v1")
        st.session_state["usmidterm_all_house_cache"] = all_house_races
    except Exception as exc:  # noqa: BLE001
        all_house_races = st.session_state.get("usmidterm_all_house_cache", {})
        fetch_errors.append(f"下院(全米集計)データ取得エラー: {exc}")
        all_house_errors = []

if not senate_races and not governor_races and not house_races and not preview_mode:
    st.error("civicAPIからデータを取得できませんでした。しばらくしてから「↻ 更新」をお試しください。「プレビュー用ダミーデータ」をオンにすると画面デザインだけ先に確認できます。")
    for e in fetch_errors:
        st.caption(e)
    st.stop()

# ---------------------------------------------------------------------------
# 1. Election Header
# ---------------------------------------------------------------------------
now_utc = datetime.utcnow()
jst_str = et_str = None
try:
    if ZoneInfo is not None:
        now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
        now_et = datetime.now(ZoneInfo("America/New_York"))
        jst_str = now_jst.strftime("%H:%M")
        et_str = now_et.strftime("%H:%M:%S")
except Exception:
    jst_str = et_str = None

if jst_str is None:
    jst_str = now_utc.strftime("%H:%M") + " UTC"

mode_label = "LIVE" if (autorefresh_on and not preview_mode) else ("PREVIEW" if preview_mode else "RESULTS")
dot_class = "on" if mode_label == "LIVE" else ""
updated_line = f"Last updated {et_str} ET / {jst_str} JST" if et_str else f"Last updated {jst_str} JST"

st.markdown(
    f"""
<div class="en-header">
  <div class="en-header-top">
    <span class="en-live-dot {dot_class}"></span>
    <span class="en-live-label">2026 MIDTERM ELECTIONS {mode_label} {'●' if mode_label=='LIVE' else ''}</span>
  </div>
  <div class="en-header-title">2026年米国中間選挙</div>
  <div class="en-header-sub">U.S. GENERAL ELECTION · NOVEMBER 3, 2026</div>
  <div class="en-header-updated">{updated_line}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. Data / Update Status Strip
# ---------------------------------------------------------------------------
n_tracked = len(senate_races) + len(governor_races) + len(all_house_races)
all_errors = fetch_errors + senate_errors + governor_errors + house_errors + (all_house_errors if not preview_mode else [])
err_note = f" ／ 取得失敗 {len(all_errors)}件" if all_errors else ""
st.markdown(
    f'<div class="en-status-strip"><span>データソース: civicAPI（非公式）／ 追跡中のレース {n_tracked}件{err_note}</span>'
    f'<span>公式選管・AP通信等の公式コールではありません</span></div>',
    unsafe_allow_html=True,
)
if all_errors:
    with st.expander("一部データの取得に失敗しています（クリックで詳細）", expanded=False):
        for e in all_errors:
            st.caption(e)
with st.expander("データと表示方法についての注記", expanded=False):
    st.caption(
        "本ページの開票データはcivicAPI（civicapi.org）から取得した非公式の参考情報です。"
        "州選管・連邦議会・AP通信等による公式の確定結果・当確(コール)ではありません。"
        "「当確(CALLED)」はAPIのcandidates.winnerフラグが立っている場合のみ表示し、"
        "単なる1位（リード）とは明確に区別しています。開票率0%のレースは投票開始前のプレースホルダーです。"
        "BALANCE OF POWERの『改選対象外』議席数は暫定値(data/us_congress_holdover_2026.json)であり、"
        "実際の最新構成に合わせて更新が必要な場合があります。"
    )

# ---------------------------------------------------------------------------
# 3. BALANCE OF POWER
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">BALANCE OF POWER</div>', unsafe_allow_html=True)

if preview_mode:
    # スペック記載の例示数値をそのままプレビューとして使う
    sb = {"total": 100, "dem_total": 44, "rep_total": 48, "uncalled": 8, "up": 33}
    hb = {"total": 435, "dem_total": 201, "rep_total": 207, "uncalled": 27}
else:
    sb = umd.senate_balance(senate_races, holdover["senate"])
    hb = umd.house_balance(all_house_races, holdover["house"])


def render_power_bar(balance: dict, control: int, dem_caption: str, rep_caption: str):
    total = balance["total"] or 1
    dem_pct = 100 * balance["dem_total"] / total
    rep_pct = 100 * balance["rep_total"] / total
    unc_pct = max(0.0, 100 - dem_pct - rep_pct)
    control_pct = 100 * control / total
    st.markdown(
        f"""
<div class="bop-row">
  <div class="bop-label">{dem_caption}<span class="bop-num">{balance['dem_total']}</span></div>
  <div class="bop-bar-wrap">
    <div class="bop-bar">
      <div class="bop-seg dem" style="width:{dem_pct:.2f}%"></div>
      <div class="bop-seg uncalled" style="width:{unc_pct:.2f}%"></div>
      <div class="bop-seg rep" style="width:{rep_pct:.2f}%"></div>
    </div>
    <div class="bop-control-line" style="left:{control_pct:.2f}%"><span>{control} TO CONTROL</span></div>
  </div>
  <div class="bop-label bop-label-right">{rep_caption}<span class="bop-num">{balance['rep_total']}</span></div>
</div>
<div class="bop-note">{balance['uncalled']} races not called</div>
""",
        unsafe_allow_html=True,
    )


b1, b2 = st.columns(2, gap="large")
with b1:
    st.markdown('<div class="bop-block"><div class="bop-heading">SENATE</div>', unsafe_allow_html=True)
    render_power_bar(sb, 51, "DEMOCRATIC<br>CAUCUS", "REPUBLICAN")
    st.markdown(f'<div class="bop-note" style="margin-top:.3rem;">{sb["up"]}議席が今回改選対象（残りは非改選・暫定値）</div></div>', unsafe_allow_html=True)
with b2:
    st.markdown('<div class="bop-block"><div class="bop-heading">HOUSE</div>', unsafe_allow_html=True)
    render_power_bar(hb, 218, "DEMOCRATIC", "REPUBLICAN")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title" style="margin-top:1rem;">GOVERNOR SUMMARY</div>', unsafe_allow_html=True)
gs = umd.governor_summary(governor_races)
st.markdown(
    f"""
<div class="gov-stat-row">
  <div class="gov-stat-tile"><div class="gov-stat-num" style="color:{DEM_CALL}">{gs['called_dem']}</div><div class="gov-stat-label">DEM CALL</div></div>
  <div class="gov-stat-tile"><div class="gov-stat-num" style="color:{REP_CALL}">{gs['called_rep']}</div><div class="gov-stat-label">REP CALL</div></div>
  <div class="gov-stat-tile"><div class="gov-stat-num" style="color:{OTHER}">{gs['called_other']}</div><div class="gov-stat-label">OTHER</div></div>
  <div class="gov-stat-tile"><div class="gov-stat-num" style="color:{SUBTEXT}">{gs['leading'] + gs['not_reporting']}</div><div class="gov-stat-label">UNCALLED</div></div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 4. LIVE WATCH STRIP（上院の中で接戦のレースを動的に抽出）
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">LIVE WATCH STRIP</div>', unsafe_allow_html=True)


def _closest_margin_races(races: dict, limit: int = 8) -> list[tuple[str, dict, dict]]:
    scored = []
    for code, race in races.items():
        margin = umd.race_margin(race)
        if margin is None:
            continue
        scored.append((abs(margin["pct_diff"]), code, race, margin))
    scored.sort(key=lambda x: x[0])
    return [(code, race, margin) for _, code, race, margin in scored[:limit]]


closest = _closest_margin_races(senate_races, limit=8)
if closest:
    chips = []
    for code, race, margin in closest:
        leader = margin["leader"]
        bucket = umd.party_bucket(leader.get("party"))
        sign = "DEM" if bucket == "dem" else ("REP" if bucket == "rep" else "OTH")
        pct = race.get("percent_reporting") or 0
        chips.append(
            f'<span class="lws-item">{code} SEN · {sign} +{abs(margin["pct_diff"]):.1f} · {pct:.0f}%</span>'
        )
    st.markdown('<div class="lws-wrap">' + '<span class="lws-sep">|</span>'.join(chips) + '</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="lws-wrap">まだ接戦の目安を表示できるレースがありません（開票開始後に表示されます）。</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 5. WATCH DESK
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">WATCH DESK</div>', unsafe_allow_html=True)

category = st.radio(
    "カテゴリ", ["ALL", "SENATE", "HOUSE", "GOVERNOR"], horizontal=True, key="um_category", label_visibility="collapsed"
)

quick_states = ["ALL"] + sorted({r for r in senate_races.keys()} | {e["code"] for e in watchlist})[:10]
state_filter = st.radio("州", quick_states, horizontal=True, key="um_state_filter", label_visibility="collapsed")


def render_race_card(label: str, subtitle: str, race: dict):
    status = umd.race_status(race)
    pct = race.get("percent_reporting") or 0
    candidates = umd.sorted_candidates(race)
    accent = accent_color(race)
    pct_label = "開票前" if pct == 0 and status == "not_reporting" else f"{pct:.0f}% REPORTING"
    status_badge_color = {"called": "#1F6F3E", "leading": "#A66A00", "not_reporting": SUBTEXT, "no_data": SUBTEXT}[status]
    status_badge_label = {"called": "✓ CALLED", "leading": "LEADING", "not_reporting": "NOT REPORTING", "no_data": "NO DATA"}[status]

    cand_html = ""
    dem_pct = rep_pct = 0.0
    for c in candidates[:2]:
        bucket = umd.party_bucket(c.get("party"))
        votes = c.get("votes") or 0
        vpct = c.get("percent") or 0
        if bucket == "dem":
            dem_pct = vpct
        elif bucket == "rep":
            rep_pct = vpct
        color = {"dem": DEM, "rep": REP}.get(bucket, OTHER)
        cand_html += (
            f'<div class="race-cand-row"><span class="race-cand-name" style="color:{color}">'
            f'{c.get("name","")}</span><span class="race-cand-pct" style="color:{color}">{vpct:.1f}%</span></div>'
            f'<div class="race-cand-votes">{votes:,}票</div>'
        )

    margin = umd.race_margin(race)
    margin_html = ""
    if margin is not None:
        leader = margin["leader"]
        bucket = umd.party_bucket(leader.get("party"))
        color = {"dem": DEM, "rep": REP}.get(bucket, OTHER)
        margin_html = (
            f'<div class="race-margin" style="color:{color};">'
            f'{party_label_ja(leader.get("party"))} +{margin["vote_diff"]:,} / +{margin["pct_diff"]:.1f}pt</div>'
        )

    st.markdown(
        f"""
<div class="race-card" style="border-left-color:{accent};">
  <div class="race-card-top">
    <span class="race-card-title">{label} · {subtitle}</span>
    <span class="race-status-badge" style="background:{status_badge_color};">{status_badge_label}</span>
  </div>
  {cand_html}
  <div class="race-bar-wrap">
    <div class="race-bar-dem" style="width:{dem_pct/2:.2f}%;"></div>
    <div class="race-bar-rep" style="width:{rep_pct/2:.2f}%;"></div>
    <div class="race-bar-mid"></div>
  </div>
  {margin_html}
  <div class="race-progress"><div class="race-progress-fill" style="width:{pct:.1f}%;"></div></div>
  <div class="race-card-pct">{pct_label}</div>
</div>
""",
        unsafe_allow_html=True,
    )


watch_items = []  # (label, subtitle, race, state_code)
if category in ("ALL", "SENATE"):
    for code, race in senate_races.items():
        watch_items.append((code, "U.S. SENATE", race, code))
if category in ("ALL", "GOVERNOR"):
    for code, race in governor_races.items():
        watch_items.append((code, "GOVERNOR", race, code))
if category in ("ALL", "HOUSE"):
    for entry in watchlist:
        race = house_races.get(entry["district"])
        if race is not None:
            watch_items.append((entry["district"], "U.S. HOUSE", race, entry["code"]))

if state_filter != "ALL":
    watch_items = [w for w in watch_items if w[3] == state_filter]

if watch_items:
    st.markdown('<div class="race-grid">', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (label, subtitle, race, _code) in enumerate(watch_items):
        with cols[i % 3]:
            render_race_card(label, subtitle, race)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("条件に一致するレースがありません。")

# ---------------------------------------------------------------------------
# 6. U.S. MAP
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">U.S. MAP</div>', unsafe_allow_html=True)
map_target = st.radio("表示するレース", ["SENATE", "GOVERNOR"], horizontal=True, key="um_map_target", label_visibility="collapsed")
races_for_map = senate_races if map_target == "SENATE" else governor_races


def build_dashboard_map(races: dict, title: str):
    locations, z, hover = [], [], []
    for code, race in races.items():
        score = umd.map_score(race)
        locations.append(code)
        z.append(score)
        candidates = umd.sorted_candidates(race)
        pct = race.get("percent_reporting") or 0
        margin = umd.race_margin(race)
        lines = [f"<b>{code}</b>", title]
        for c in candidates[:2]:
            lines.append(f"{c.get('name','')} {c.get('percent') or 0:.1f}%")
        if margin is not None:
            leader_bucket = umd.party_bucket(margin["leader"].get("party"))
            sign = "DEM" if leader_bucket == "dem" else ("REP" if leader_bucket == "rep" else "OTH")
            lines.append(f"{sign} +{margin['vote_diff']:,}")
        lines.append(f"{pct:.0f}% reporting")
        hover.append("<br>".join(lines))

    fig = go.Figure(
        go.Choropleth(
            locations=locations,
            z=z,
            locationmode="USA-states",
            text=hover,
            hovertemplate="%{text}<extra></extra>",
            colorscale=[
                [0.0, DEM_CALL], [0.25, DEM_LEAD], [0.5, NODATA], [0.75, REP_LEAD], [1.0, REP_CALL],
            ],
            zmin=-2, zmax=2,
            showscale=False,
            marker_line_color="#FFFFFF",
            marker_line_width=1,
        )
    )
    fig.update_layout(
        geo=dict(scope="usa", projection=dict(type="albers usa"), showlakes=False, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=660,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


if races_for_map:
    st.plotly_chart(build_dashboard_map(races_for_map, map_target), use_container_width=True)
    st.markdown(
        f"""
<div class="pill-row" style="font-size:.78rem;">
  <span><span style="display:inline-block;width:10px;height:10px;background:{DEM_CALL};margin-right:.3rem;"></span>DEM CALL</span>
  <span><span style="display:inline-block;width:10px;height:10px;background:{DEM_LEAD};margin-right:.3rem;"></span>DEM LEAD</span>
  <span><span style="display:inline-block;width:10px;height:10px;background:{REP_LEAD};margin-right:.3rem;"></span>REP LEAD</span>
  <span><span style="display:inline-block;width:10px;height:10px;background:{REP_CALL};margin-right:.3rem;"></span>REP CALL</span>
  <span><span style="display:inline-block;width:10px;height:10px;background:{NODATA};margin-right:.3rem;"></span>NO DATA</span>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.info("地図に表示できるデータがまだありません。")

# ---------------------------------------------------------------------------
# 7. ALL RACES（表形式の補助ビュー）
# ---------------------------------------------------------------------------
with st.expander("ALL RACES（すべてのレースを表で見る）", expanded=False):
    def _table(races: dict) -> pd.DataFrame:
        rows = []
        for code, race in races.items():
            candidates = umd.sorted_candidates(race)
            lead = candidates[0] if candidates else None
            runner = candidates[1] if len(candidates) > 1 else None
            margin = umd.race_margin(race)
            rows.append({
                "州/区": code,
                "状態": STATUS_LABEL_JA[umd.race_status(race)],
                "開票率": race.get("percent_reporting") or 0,
                "首位候補": lead.get("name") if lead else "—",
                "首位政党": party_label_ja(lead.get("party")) if lead else "—",
                "首位得票率": lead.get("percent") if lead else None,
                "次点候補": runner.get("name") if runner else "—",
                "次点得票率": runner.get("percent") if runner else None,
                "票差": margin["vote_diff"] if margin else None,
            })
        df = pd.DataFrame(rows)
        return df.sort_values("州/区").reset_index(drop=True) if not df.empty else df

    st.markdown("**上院(Senate)**")
    st.dataframe(_table(senate_races), use_container_width=True, hide_index=True)
    st.markdown("**知事選(Governor)**")
    st.dataframe(_table(governor_races), use_container_width=True, hide_index=True)
    st.markdown("**下院(House) 注目レース一覧**")
    st.dataframe(_table(house_races), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# 8. データソース・免責事項
# ---------------------------------------------------------------------------
st.markdown(
    """
<div class="en-footer">
データソース: civicAPI（civicapi.org、認証不要・無料の非公式サードパーティAPI）。州選管・連邦議会・AP通信等による
公式の確定結果・当確ではなく、参考情報としての提供です。BALANCE OF POWERの非改選議席数は暫定値であり、
data/us_congress_holdover_2026.json を編集することで最新の構成に合わせて更新できます。
下院の注目レース一覧は data/us_house_watchlist_2026.json で編集可能な初期セットであり、
435選挙区すべてを網羅するものではありません（BALANCE OF POWERの下院集計のみ、全50州の本選データを個別に集計しています）。
</div>
""",
    unsafe_allow_html=True,
)

st.caption("v0.9.40 · US MIDTERMS 2026 · Election Night Dashboard · civicAPI（非公式）")
