from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

import civic_api as ca

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

ELECTION_DATE = "2026-11-03"
VERSION = "0.10.1"

STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia"
}

# 119th Congress baseline, checked against senate.gov in 2026.
# Democratic caucus = 45 Democrats + 2 Independents who caucus with Democrats.
SENATE_CURRENT_DEM_CAUCUS = 47
SENATE_CURRENT_REP = 53
# 2026 ballot: 33 regular Class II seats + the OH/FL special elections.
SENATE_2026_DEM_CAUCUS_SEATS = 13
SENATE_2026_REP_SEATS = 22
SENATE_HOLDOVER_DEM_CAUCUS = SENATE_CURRENT_DEM_CAUCUS - SENATE_2026_DEM_CAUCUS_SEATS  # 34
SENATE_HOLDOVER_REP = SENATE_CURRENT_REP - SENATE_2026_REP_SEATS  # 31
SENATE_SEATS_ON_BALLOT = 35

DEFAULT_WATCH_STATES = ["NC", "TX", "ME", "OH", "AK"]

st.markdown("""
<style>
.us-wrap {font-family:"Meiryo","Yu Gothic",system-ui,sans-serif;}
.us-kicker {font-size:.77rem;font-weight:800;letter-spacing:.11em;color:#667085;margin-bottom:.35rem;}
.us-title {font-family:Georgia,"Yu Mincho",serif;font-size:2.6rem;font-weight:800;line-height:1.05;margin-bottom:.35rem;}
.us-deck {color:#667085;margin-bottom:1.25rem;line-height:1.7;}
.us-card {border:1px solid #D7DBE0;border-top:4px solid #1F4E79;background:white;padding:1rem 1.1rem;border-radius:2px;min-height:112px;}
.us-card.red {border-top-color:#B42318}.us-card.blue {border-top-color:#175CD3}.us-card.gold {border-top-color:#B54708}
.us-label {font-size:.74rem;font-weight:800;color:#667085;letter-spacing:.08em;text-transform:uppercase;}
.us-value {font-size:1.65rem;font-weight:800;margin-top:.18rem;}
.us-sub {font-size:.83rem;color:#667085;margin-top:.3rem;}
.race-box {border:1px solid #D7DBE0;padding:1rem 1.1rem;margin:.45rem 0;background:#fff;}
.race-name {font-weight:800;font-size:1.02rem}.race-meta {color:#667085;font-size:.82rem;margin-top:.18rem}
.candidate-row {display:flex;gap:1rem;align-items:baseline;border-bottom:1px solid #EEE;padding:.55rem 0;}
.candidate-row:last-child {border-bottom:none}.candidate-name {font-weight:800;min-width:280px}.candidate-vote {font-variant-numeric:tabular-nums;font-weight:700}.candidate-pct {font-variant-numeric:tabular-nums;color:#475467;}
.call-pill {font-size:.72rem;background:#111;color:white;border-radius:999px;padding:.15rem .45rem;margin-left:.4rem;font-weight:800;}
.small-note {font-size:.82rem;color:#667085;line-height:1.6;}
.seat-board {border:1px solid #D7DBE0;background:#fff;padding:1rem 1.15rem 1.1rem;margin:.35rem 0 1.1rem;}
.seat-head {display:flex;justify-content:space-between;gap:1rem;align-items:flex-end;margin-bottom:.65rem;}
.seat-title {font-size:1rem;font-weight:900;letter-spacing:.04em;}
.seat-meta {font-size:.78rem;color:#667085;text-align:right;}
.seat-meter {position:relative;height:36px;display:flex;border:1px solid #BFC5CC;overflow:visible;background:#EAECF0;}
.seat-dem {background:#2F6BFF;height:100%;}.seat-und {background:#EAECF0;height:100%;}.seat-oth {background:#7F56D9;height:100%;}.seat-rep {background:#D64545;height:100%;}
.seat-50 {position:absolute;left:50%;top:-7px;bottom:-7px;border-left:2px solid #111;z-index:4;}
.seat-50-label {position:absolute;left:50%;transform:translateX(-50%);top:-25px;background:#111;color:#fff;padding:1px 5px;font-size:.69rem;font-weight:800;}
.seat-labels {display:grid;grid-template-columns:1fr 1fr 1fr;margin-top:.55rem;font-size:.82rem;font-weight:800;}
.seat-labels .center{text-align:center;color:#667085}.seat-labels .right{text-align:right}
.watch-note {font-size:.78rem;color:#667085;margin-top:.2rem;margin-bottom:.8rem;}
.quick-state {font-size:.75rem;color:#667085;}
</style>
""", unsafe_allow_html=True)


def set_state_filter(code: str):
    st.session_state["us_state_filter"] = code


if st.button("← ポータルTOP", key="us_back_top"):
    st.session_state["portal_page"] = "home"
    st.rerun()

st.markdown('<div class="us-kicker">UNITED STATES · 2026 MIDTERM ELECTIONS</div>', unsafe_allow_html=True)
st.markdown('<div class="us-title">アメリカ中間選挙 開票デスク</div>', unsafe_allow_html=True)
st.markdown('<div class="us-deck">civicAPIから2026年11月3日のレースを取得し、上院・下院・知事選を監視します。上院は100議席全体の勢力ボード、注目州は専用WATCH DESKで確認できます。データ提供：civicAPI。</div>', unsafe_allow_html=True)

if "us_state_filter" not in st.session_state:
    st.session_state["us_state_filter"] = "ALL"

ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.2,1.25,1.2,2.25])
with ctrl1:
    auto_refresh = st.toggle("10秒自動更新", value=False, help="選挙当日はON推奨。")
with ctrl2:
    include_test = st.toggle("選択レースをテスト表示", value=False, help="civicAPIのtestdataオプションを使い、開票前でもレース詳細を確認しやすくします。")
with ctrl3:
    if st.button("今すぐ再取得", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with ctrl4:
    state_filter = st.selectbox(
        "州で絞り込み",
        ["ALL"] + sorted(STATE_NAMES),
        format_func=lambda x: "全米" if x == "ALL" else f"{x} · {STATE_NAMES.get(x,x)}",
        key="us_state_filter",
    )

if auto_refresh and st_autorefresh is not None:
    st_autorefresh(interval=10_000, limit=None, key="us-midterms-autorefresh")


@st.cache_data(ttl=8, show_spinner=False)
def api_status():
    return ca.get_status()


@st.cache_data(ttl=10, show_spinner=False)
def load_races():
    merged = []
    seen = set()
    for election_type in ("senate", "house", "governor"):
        raw = ca.search_races(
            country="US", election_type=election_type,
            start_date=ELECTION_DATE, end_date=ELECTION_DATE, limit=2000
        )
        for race in ca.extract_race_list(raw):
            key = ca.race_id(race) or (ca.race_name(race), ca.province_code(race), ca.election_type(race))
            if key not in seen:
                seen.add(key)
                merged.append(race)
    # Also perform one broad date search. This protects against provider-side
    # election_type naming differences and fills any category the filtered calls miss.
    raw = ca.search_races(country="US", start_date=ELECTION_DATE, end_date=ELECTION_DATE, limit=5000)
    for race in ca.extract_race_list(raw):
        key = ca.race_id(race) or (ca.race_name(race), ca.province_code(race), ca.election_type(race))
        if key not in seen:
            seen.add(key)
            merged.append(race)
    return merged


@st.cache_data(ttl=8, show_spinner=False)
def load_race_detail(rid: str, testdata: bool):
    return ca.extract_race_detail(ca.get_race(rid, precinct=False, testdata=testdata))


@st.cache_data(ttl=60, show_spinner=False)
def load_map_svg(rid: str, testdata: bool):
    return ca.get_race_map_svg(rid, testdata=testdata)


status_error = None
try:
    status = api_status()
except Exception as exc:
    status = {}
    status_error = str(exc)

fetch_error = None
try:
    races = load_races()
except Exception as exc:
    races = []
    fetch_error = str(exc)


def margin_info(race: dict):
    """Return absolute top-two gap using available vote totals and percentages."""
    cs = ca.candidates(race)
    if len(cs) < 2:
        return None, None
    with_votes = [c for c in cs if ca.candidate_votes(c) is not None]
    vote_gap = None
    if len(with_votes) >= 2:
        top = sorted(with_votes, key=lambda c: ca.candidate_votes(c) or 0, reverse=True)[:2]
        vote_gap = abs((ca.candidate_votes(top[0]) or 0) - (ca.candidate_votes(top[1]) or 0))
    with_pct = [c for c in cs if ca.candidate_percent(c) is not None]
    pct_gap = None
    if len(with_pct) >= 2:
        top = sorted(with_pct, key=lambda c: ca.candidate_percent(c) or 0, reverse=True)[:2]
        pct_gap = abs((ca.candidate_percent(top[0]) or 0.0) - (ca.candidate_percent(top[1]) or 0.0))
    return vote_gap, pct_gap


# Normalize race metadata once. Keep an unfiltered copy for the national board and WATCH DESK.
all_rows = []
for r in races:
    rid = ca.race_id(r)
    typ = ca.election_type(r)
    state = ca.province_code(r)
    name = ca.race_name(r) or f"Race {rid}"
    rep = ca.reporting_pct(r)
    lead = ca.leader(r)
    vote_gap, pct_gap = margin_info(r)
    all_rows.append({
        "race": r, "race_id": rid, "type": typ, "state": state, "name": name,
        "reporting": rep,
        "leader_name": ca.candidate_name(lead) if lead else "",
        "leader_party": ca.candidate_party(lead) if lead else "",
        "called": ca.candidate_called(lead) if lead else False,
        "vote_gap": vote_gap,
        "pct_gap": pct_gap,
    })

rows = all_rows if state_filter == "ALL" else [x for x in all_rows if x["state"] == state_filter]
senate_all = [x for x in all_rows if x["type"] == "Senate"]
house_all = [x for x in all_rows if x["type"] == "House"]
gov_all = [x for x in all_rows if x["type"] == "Governor"]
senate = [x for x in rows if x["type"] == "Senate"]
house = [x for x in rows if x["type"] == "House"]
gov = [x for x in rows if x["type"] == "Governor"]
other = [x for x in rows if x["type"] not in {"Senate", "House", "Governor"}]

status_text = str(status.get("status", "unknown")) if status else "unavailable"
mc1, mc2, mc3, mc4 = st.columns(4)
with mc1:
    st.markdown(f'<div class="us-card blue"><div class="us-label">API STATUS</div><div class="us-value">{escape(status_text.upper())}</div><div class="us-sub">{escape(status_error or "civicAPI v2")}</div></div>', unsafe_allow_html=True)
with mc2:
    st.markdown(f'<div class="us-card"><div class="us-label">SENATE</div><div class="us-value">{len(senate_all)}</div><div class="us-sub">全米の取得レース数</div></div>', unsafe_allow_html=True)
with mc3:
    st.markdown(f'<div class="us-card red"><div class="us-label">HOUSE</div><div class="us-value">{len(house_all)}</div><div class="us-sub">全米の取得レース数</div></div>', unsafe_allow_html=True)
with mc4:
    st.markdown(f'<div class="us-card gold"><div class="us-label">GOVERNOR</div><div class="us-value">{len(gov_all)}</div><div class="us-sub">全米の取得レース数</div></div>', unsafe_allow_html=True)

if fetch_error:
    st.error("civicAPIから2026年11月3日のレース一覧を取得できませんでした。ネット接続・API状態を確認してください。\n\n" + fetch_error)
    st.info("画面実装自体は入っています。APIが応答すれば一覧・勢力ボード・WATCH DESK・レース詳細が動きます。")
else:
    filter_txt = "全米" if state_filter == "ALL" else state_filter
    st.caption(f"取得 {len(all_rows):,}レース · 表示範囲 {filter_txt} · Election date: {ELECTION_DATE} · 最終画面更新 {datetime.now().strftime('%H:%M:%S')}")


# ---- Senate control board -------------------------------------------------
called_dem = sum(1 for x in senate_all if x["called"] and ca.party_bucket(x["leader_party"]) == "DEM")
called_rep = sum(1 for x in senate_all if x["called"] and ca.party_bucket(x["leader_party"]) == "REP")
called_oth = sum(1 for x in senate_all if x["called"] and ca.party_bucket(x["leader_party"]) == "OTH")
seat_dem = SENATE_HOLDOVER_DEM_CAUCUS + called_dem
seat_rep = SENATE_HOLDOVER_REP + called_rep
seat_oth = called_oth
seat_und = max(0, 100 - seat_dem - seat_rep - seat_oth)

st.markdown("### SENATE CONTROL")
seat_html = f'''
<div class="seat-board">
  <div class="seat-head">
    <div class="seat-title">100 SEATS · 50 LINE</div>
    <div class="seat-meta">非改選ベース: 民主党会派 {SENATE_HOLDOVER_DEM_CAUCUS} / 共和党 {SENATE_HOLDOVER_REP}<br>2026改選・特別選挙: {SENATE_SEATS_ON_BALLOT}議席</div>
  </div>
  <div class="seat-meter">
    <div class="seat-dem" style="width:{seat_dem}%"></div>
    <div class="seat-oth" style="width:{seat_oth}%"></div>
    <div class="seat-und" style="width:{seat_und}%"></div>
    <div class="seat-rep" style="width:{seat_rep}%"></div>
    <div class="seat-50"></div><div class="seat-50-label">50</div>
  </div>
  <div class="seat-labels">
    <div>民主党会派 {seat_dem}</div>
    <div class="center">未確定 {seat_und} / その他 {seat_oth} · 単独過半数 51</div>
    <div class="right">共和党 {seat_rep}</div>
  </div>
</div>
'''
st.markdown(seat_html, unsafe_allow_html=True)
st.caption("民主党会派の非改選ベースには、民主党と会派を組む無所属を含みます。APIで当確が確認できたレースだけを積み上げ、未当確は中央の未確定に残します。50対50の場合の多数派は副大統領の党派等で決まります。")

# One-click state filters. These are editable monitoring shortcuts, not forecasts.
st.markdown('<div class="quick-state">QUICK STATE FILTER</div>', unsafe_allow_html=True)
quick_cols = st.columns(len(DEFAULT_WATCH_STATES) + 1)
quick_cols[0].button("ALL", key="quick_all", use_container_width=True, on_click=set_state_filter, args=("ALL",))
for col, code in zip(quick_cols[1:], DEFAULT_WATCH_STATES):
    col.button(code, key=f"quick_{code}", use_container_width=True, on_click=set_state_filter, args=(code,))

# Statewide map. No external GeoJSON is required.
statewide = [x for x in senate + gov if x["state"] in STATE_NAMES]
map_rows = []
priority = {"Senate": 2, "Governor": 1}
by_state = {}
for x in statewide:
    if x["state"] not in by_state or priority.get(x["type"], 0) > priority.get(by_state[x["state"]]["type"], 0):
        by_state[x["state"]] = x
for state, x in by_state.items():
    bucket = ca.party_bucket(x["leader_party"])
    map_rows.append({"state": state, "status": bucket if x["leader_name"] else "NO DATA", "race": x["name"], "leader": x["leader_name"] or "未集計"})

if map_rows:
    map_df = pd.DataFrame(map_rows)
    fig = px.choropleth(
        map_df,
        locations="state",
        locationmode="USA-states",
        scope="usa",
        color="status",
        hover_name="race",
        hover_data={"state": True, "leader": True, "status": True},
        color_discrete_map={"DEM":"#2F6BFF", "REP":"#D64545", "OTH":"#8B6FC0", "NO DATA":"#D0D5DD"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=420, legend_title_text="Leader")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("州単位の上院・知事選データを取得すると、ここに全米マップが表示されます。外部GeoJSONは不要です。")


def race_table(items: list[dict], limit: int | None = None):
    data = []
    src = items[:limit] if limit else items
    for x in src:
        data.append({
            "州": x["state"],
            "種別": x["type"],
            "レース": x["name"],
            "開票率": None if x["reporting"] is None else round(x["reporting"], 1),
            "リード/当確": x["leader_name"],
            "党派": x["leader_party"],
            "票差": x["vote_gap"],
            "pt差": None if x["pct_gap"] is None else round(x["pct_gap"], 2),
            "当確": "✓" if x["called"] else "",
            "race_id": x["race_id"],
        })
    return pd.DataFrame(data)


def watch_sort_key(x: dict):
    # Uncalled races first, then the smallest known percentage gap, then higher reporting.
    pct = x["pct_gap"] if x["pct_gap"] is not None else 9999.0
    vote = x["vote_gap"] if x["vote_gap"] is not None else 10**18
    reporting = x["reporting"] if x["reporting"] is not None else -1.0
    return (1 if x["called"] else 0, pct, vote, -reporting, x["state"], x["name"])


def state_sort_key(x: dict):
    return (x["state"], x["type"], x["name"])


def reporting_sort_key(x: dict):
    reporting = x["reporting"] if x["reporting"] is not None else -1.0
    return (-reporting, x["state"], x["name"])


tab_over, tab_watch, tab_sen, tab_house, tab_gov, tab_detail = st.tabs(["OVERVIEW", "WATCH DESK", "SENATE", "HOUSE", "GOVERNOR", "RACE DETAIL"])

with tab_over:
    st.subheader("CALL MONITOR")
    called_rows = [x for x in all_rows if x["called"]]
    if called_rows:
        called_rows = sorted(called_rows, key=lambda x: (x["type"], x["state"], x["name"]))
        st.dataframe(race_table(called_rows, limit=120), use_container_width=True, hide_index=True, height=360)
    else:
        st.info("当確（CALL）が入ると、ここに一覧表示します。")

    st.subheader("全レース一覧")
    combined = senate + gov + house
    if combined:
        st.dataframe(race_table(combined, limit=120), use_container_width=True, hide_index=True, height=500)
    elif not fetch_error:
        st.warning("該当レースがまだAPIに登録されていないか、検索条件とAPI側の分類が一致していません。")
    if other:
        with st.expander(f"その他のレース {len(other)}件"):
            st.dataframe(race_table(other, limit=100), use_container_width=True, hide_index=True)

with tab_watch:
    st.subheader("MY WATCH")
    st.markdown('<div class="watch-note">初期値は NC / TX / ME / OH / AK。自由に追加・削除できます。予測や評価ではなく、監視対象を絞るための表示設定です。</div>', unsafe_allow_html=True)
    wc1, wc2, wc3 = st.columns([2.3, 1.5, 1.4])
    with wc1:
        watch_states = st.multiselect(
            "監視する州",
            options=sorted(STATE_NAMES),
            default=[x for x in DEFAULT_WATCH_STATES if x in STATE_NAMES],
            format_func=lambda x: f"{x} · {STATE_NAMES[x]}",
            key="us_watch_states",
        )
    with wc2:
        watch_types = st.multiselect("レース種別", ["Senate", "House", "Governor"], default=["Senate"], key="us_watch_types")
    with wc3:
        watch_sort = st.selectbox("並び順", ["未当確→票差の小さい順", "州順", "開票率の高い順"], key="us_watch_sort")

    watch_items = [x for x in all_rows if x["state"] in watch_states and x["type"] in watch_types]
    if watch_sort == "州順":
        watch_items = sorted(watch_items, key=state_sort_key)
    elif watch_sort == "開票率の高い順":
        watch_items = sorted(watch_items, key=reporting_sort_key)
    else:
        watch_items = sorted(watch_items, key=watch_sort_key)

    wm1, wm2, wm3, wm4 = st.columns(4)
    wm1.metric("監視レース", len(watch_items))
    wm2.metric("未当確", sum(1 for x in watch_items if not x["called"]))
    wm3.metric("CALL", sum(1 for x in watch_items if x["called"]))
    reporting_values = [x["reporting"] for x in watch_items if x["reporting"] is not None]
    wm4.metric("最大開票率", "—" if not reporting_values else f"{max(reporting_values):.1f}%")

    if watch_items:
        st.dataframe(race_table(watch_items, limit=120), use_container_width=True, hide_index=True, height=560)
    else:
        st.info("選択した州・種別に該当するレースはまだ取得されていません。")

with tab_sen:
    st.dataframe(race_table(senate), use_container_width=True, hide_index=True, height=560) if senate else st.info("上院レースはまだ取得されていません。")

with tab_house:
    st.dataframe(race_table(house), use_container_width=True, hide_index=True, height=620) if house else st.info("下院レースはまだ取得されていません。")

with tab_gov:
    st.dataframe(race_table(gov), use_container_width=True, hide_index=True, height=560) if gov else st.info("知事選レースはまだ取得されていません。")

with tab_detail:
    selectable = senate + gov + house + other
    if not selectable:
        st.info("レース一覧を取得できると、ここで1レースずつ詳細を確認できます。")
    else:
        labels = [f"{x['state'] or '--'} | {x['type']} | {x['name']} | ID {x['race_id']}" for x in selectable]
        idx = st.selectbox("レースを選択", range(len(selectable)), format_func=lambda i: labels[i])
        selected = selectable[idx]
        rid = selected["race_id"]
        if not rid:
            st.error("このレースにはrace_idが見つかりません。")
        else:
            try:
                detail = load_race_detail(rid, include_test)
            except Exception as exc:
                detail = selected["race"]
                st.error(f"レース詳細の取得に失敗しました: {exc}")

            name = ca.race_name(detail) or selected["name"]
            rep = ca.reporting_pct(detail)
            cs = ca.candidates(detail)
            st.subheader(name)
            a, b, c, d = st.columns(4)
            a.metric("開票・報告率", "—" if rep is None else f"{rep:.1f}%")
            total_votes = sum(v for v in (ca.candidate_votes(x) for x in cs) if v is not None)
            b.metric("候補者得票計", f"{total_votes:,}" if total_votes else "—")
            winner = next((x for x in cs if ca.candidate_called(x)), None)
            c.metric("CALL", ca.candidate_name(winner) if winner else "未当確")
            vg, pg = margin_info(detail)
            d.metric("1-2位差", "—" if vg is None else f"{vg:,}票", None if pg is None else f"{pg:.2f}pt")

            if cs:
                sorted_cs = sorted(cs, key=lambda x: ca.candidate_votes(x) or 0, reverse=True)
                html = ['<div class="race-box">']
                for cand in sorted_cs:
                    nm = escape(ca.candidate_name(cand))
                    party = escape(ca.candidate_party(cand))
                    votes = ca.candidate_votes(cand)
                    pct = ca.candidate_percent(cand)
                    call = '<span class="call-pill">CALL</span>' if ca.candidate_called(cand) else ''
                    inc = ' · Inc.' if ca.candidate_incumbent(cand) else ''
                    if votes is not None and pct is not None:
                        row_html = f'<div class="candidate-row"><div class="candidate-name">{nm} <span style="color:#667085;font-weight:600">{party}{inc}</span>{call}</div><div class="candidate-vote">{votes:,}票</div><div class="candidate-pct">{pct:.2f}%</div></div>'
                    elif votes is not None:
                        row_html = f'<div class="candidate-row"><div class="candidate-name">{nm} <span style="color:#667085;font-weight:600">{party}{inc}</span>{call}</div><div class="candidate-vote">{votes:,}票</div></div>'
                    else:
                        row_html = f'<div class="candidate-row"><div class="candidate-name">{nm} <span style="color:#667085;font-weight:600">{party}{inc}</span>{call}</div><div class="candidate-vote">未集計</div></div>'
                    html.append(row_html)
                html.append('</div>')
                st.markdown(''.join(html), unsafe_allow_html=True)

                # Session-level history: useful while the app stays open, no write-back needed.
                hist_key = f"us_hist_{rid}_{include_test}"
                hist = st.session_state.setdefault(hist_key, [])
                snap = ca.snapshot(detail)
                sig = tuple((x["name"], x["votes"]) for x in snap["candidates"])
                prev_sig = hist[-1]["_sig"] if hist else None
                if sig != prev_sig:
                    snap["_sig"] = sig
                    hist.append(snap)
                    if len(hist) > 500:
                        del hist[:-500]
                if len(hist) >= 2:
                    chart_rows = []
                    for h in hist:
                        t = h["captured_at"]
                        for cand in h["candidates"]:
                            if cand["votes"] is not None:
                                chart_rows.append({"time": t, "candidate": cand["name"], "votes": cand["votes"]})
                    if chart_rows:
                        chart_df = pd.DataFrame(chart_rows)
                        fig2 = px.line(chart_df, x="time", y="votes", color="candidate", markers=True)
                        fig2.update_layout(height=360, margin=dict(l=0, r=0, t=20, b=0), legend_title_text="")
                        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("候補者データはまだありません。")

            map_col, raw_col = st.columns([1, 1])
            with map_col:
                if st.button("このレースのAPI地図を表示", use_container_width=True):
                    try:
                        svg = load_map_svg(rid, include_test)
                        st.components.v1.html(svg, height=520, scrolling=True)
                    except Exception as exc:
                        st.warning(f"API地図を表示できませんでした: {exc}")
            with raw_col:
                with st.expander("APIレスポンス（確認用）"):
                    st.json(detail)

st.markdown("---")
st.markdown('<div class="small-note">Data: civicAPI. 本画面はcivicAPIの公開APIを利用しています。重要な数値は各州・郡の公式選挙当局でも確認してください。上院の非改選ベースは2026年のU.S. Senate公式党派構成・Class II一覧を基にした固定値です。全米州地図はPlotly内蔵境界を使用しているため、現段階では追加の地図ファイルは不要です。</div>', unsafe_allow_html=True)
