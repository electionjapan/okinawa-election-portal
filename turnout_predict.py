"""
投票率予測ページ。既存の開票速報ページ(live_results.py / live_data.py)には一切手を
加えず、完全に独立したモジュールとして実装する。

データソース:
  - 過去4選挙の固定参考値 → data/turnout_predict_history.json（バンドル同梱）
  - 今回2026年知事選の実績時系列 → Googleスプレッドシート「02A_投票速報入力」
    （時刻ごとにブロックが縦に並ぶ形式。各ブロックの41市町村分を合算して
    県全体の当日投票率を算出する）
  - 今回2026年知事選の固定値（当日有権者数・期日前投票者数）→ このファイル内の定数
    （投票終了後まで変わらない値のため固定でよいとユーザーに確認済み）
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

from portal_config import GOOGLE_SHEET_ID
SHEET_ID = GOOGLE_SHEET_ID
GID_02A = 87116811 if False else None  # gid未確定の場合はシート名でgvizアクセスする

RED = "#C93238"
BLUE = "#1675B9"
GRAY = "#8E8E8E"

CHECKPOINTS = ["10:00", "11:00", "14:00", "16:00", "18:00", "19:30"]
FINAL_LABEL = "最終（期日前等含む）"

# 今回2026年知事選の固定値（投票終了まで変わらないためユーザー確認のうえ固定）
CURRENT_ELECTORATE = 1_165_704
CURRENT_EARLY_VOTERS = 347_170
CURRENT_EARLY_EQUIV_RATE = 100 * CURRENT_EARLY_VOTERS / CURRENT_ELECTORATE  # ≒29.7820


class FetchError(RuntimeError):
    pass


def _fetch_sheet_gviz(sheet_name: str, timeout: float = 15.0, headers: int | None = 0) -> pd.DataFrame:
    """GViz CSVを生の行列として取得。headersを変えて再試行できるようにする。"""
    headers_q = "" if headers is None else f"&headers={headers}"
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(sheet_name)}{headers_q}"
    )
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 OkinawaElectionPortal/0.9.33"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content = resp.read()
    except Exception as e:
        raise FetchError(str(e))
    if status != 200:
        raise FetchError(f"HTTP {status}")
    text = content.decode("utf-8-sig", errors="replace")
    if text.lstrip().lower().startswith("<!doctype html") or "<html" in text[:400].lower():
        raise FetchError("CSVではなくHTMLが返りました。共有設定と接続先IDを確認してください。")
    return pd.read_csv(io.StringIO(text), header=None, dtype=str, keep_default_na=False)


def _row_text(raw: pd.DataFrame, r: int) -> str:
    vals = []
    for v in raw.iloc[r].tolist():
        t = str(v).strip()
        if t and t.lower() != "nan":
            vals.append(t)
    return " ".join(vals)


def _num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "―"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


_TIME_TOKENS = ["10:00", "11:00", "14:00", "16:00", "18:00", "19:30"]
N_MUNI = 41

# 02A_投票速報入力の固定列インデックス（列見出しの検出に失敗した場合のフォールバック）
COL_ELECTORATE_FIXED = 4   # E列 当日有権者数_計
COL_VOTERS_FIXED = 7       # H列 投票者数_計
COL_NAME_FIXED = 1         # B列 市町村名

# 全県当日有権者数（固定・投票終了まで変わらない）。合計の妥当性チェックに使う。
ELECTORATE_SANITY_TARGET = CURRENT_ELECTORATE
ELECTORATE_SANITY_TOLERANCE = 0.02  # ±2%まで許容


def _find_col(header: list, must_contain: list, must_not_contain: list = ()):
    """ヘッダーの表記ゆれ（全角スペース混入・末尾空白など）を吸収して列を探す。"""
    for i, h in enumerate(header):
        t = str(h).strip().replace("\u3000", "")
        if all(k in t for k in must_contain) and not any(k in t for k in must_not_contain):
            return i
    return None


def _parse_one_block(raw: pd.DataFrame, label: str, data_start: int, name_col: int, source_note: str):
    n_rows, n_cols = raw.shape
    col_electorate = name_col + 3
    col_voters = name_col + 6
    votes_sum = 0.0
    elect_sum = 0.0
    n_valid = 0
    names_seen = 0
    for rr in range(data_start, min(data_start + N_MUNI, n_rows)):
        if name_col >= n_cols:
            break
        name = str(raw.iat[rr, name_col]).strip()
        if not name:
            break
        names_seen += 1
        if col_electorate >= n_cols or col_voters >= n_cols:
            continue
        e = _num(raw.iat[rr, col_electorate])
        v = _num(raw.iat[rr, col_voters])
        if e is not None and v is not None:
            elect_sum += e
            votes_sum += v
            n_valid += 1
    rate_raw = round(100 * votes_sum / elect_sum, 4) if elect_sum > 0 else None
    reasons = []
    adopted = True
    if n_valid < N_MUNI:
        adopted = False
        reasons.append(f"{n_valid}/{N_MUNI}自治体")
    if elect_sum > 0:
        diff_ratio = abs(elect_sum - ELECTORATE_SANITY_TARGET) / ELECTORATE_SANITY_TARGET
        if diff_ratio > ELECTORATE_SANITY_TOLERANCE:
            adopted = False
            reasons.append(f"有権者合計が想定から{diff_ratio*100:.1f}%乖離")
    if votes_sum <= 0:
        adopted = False
        reasons.append("投票者数が0")
    return {
        "votes_total": votes_sum if n_valid else None,
        "electorate_total": elect_sum if n_valid else None,
        "rate": rate_raw if adopted else None,
        "rate_raw": rate_raw,
        "n_munis": n_valid,
        "adopted": adopted,
    }, {
        "時刻": label, "検出方法": source_note, "自治体数": f"{n_valid}/{N_MUNI}",
        "有権者数合計": None if elect_sum == 0 else int(elect_sum),
        "投票者数合計": None if votes_sum == 0 else int(votes_sum),
        "投票率": None if rate_raw is None else f"{rate_raw:.2f}%",
        "判定": "実績として採用" if adopted else "未採用",
        "理由": "／".join(reasons),
    }


def parse_turnout_blocks(raw: pd.DataFrame):
    """
    02Aを解析する。GVizがタイトル/ヘッダーを欠落・結合しても、
    各ブロック先頭の「那覇市」をアンカーにして復元できる。
    """
    n_rows, n_cols = raw.shape
    labels = CHECKPOINTS + [FINAL_LABEL]
    results = {}
    debug_rows = []

    # A: タイトル行から検出。列Aだけでなく行全体を検索する。
    title_hits = []
    for r in range(n_rows):
        text = _row_text(raw, r)
        if "投票速報" not in text:
            continue
        label = FINAL_LABEL if "最終" in text else next((t for t in CHECKPOINTS if t in text), None)
        if label:
            title_hits.append((label, r, text))

    for label, r, text in title_hits:
        # タイトル後3行以内で「那覇市」を探し、その列を自治体名列として使う。
        anchor = None
        for rr in range(r + 1, min(r + 5, n_rows)):
            for cc in range(n_cols):
                if str(raw.iat[rr, cc]).strip() == "那覇市":
                    anchor = (rr, cc)
                    break
            if anchor:
                break
        if anchor:
            entry, dbg = _parse_one_block(raw, label, anchor[0], anchor[1], "タイトル＋那覇市アンカー")
            dbg["見つかったタイトル行"] = text
            results[label] = entry
            debug_rows.append(dbg)

    # B: タイトルがGVizに消されても、各ブロックに固定で存在する「那覇市」を全件探す。
    # 02Aには7ブロックが縦に同順で並ぶため、上から10/11/14/16/18/19:30/最終に対応する。
    anchors = []
    for r in range(n_rows):
        for c in range(n_cols):
            if str(raw.iat[r, c]).strip() == "那覇市":
                anchors.append((r, c))
                break
    anchors = sorted(set(anchors))
    if anchors:
        for i, (r, c) in enumerate(anchors[:len(labels)]):
            label = labels[i]
            if label in results:
                continue
            entry, dbg = _parse_one_block(raw, label, r, c, "那覇市アンカー（タイトル欠落フォールバック）")
            dbg["見つかったタイトル行"] = "（GViz出力ではタイトル行を取得できず）"
            results[label] = entry
            debug_rows.append(dbg)

    debug_rows.sort(key=lambda d: labels.index(d["時刻"]) if d["時刻"] in labels else 999)
    return results, debug_rows


@st.cache_data(ttl=12, show_spinner=False)
def load_current_timeseries():
    # GVizのヘッダー推測はシート内容によって挙動が変わるため複数方式を試し、
    # 最も多くブロックを復元できた結果を採用する。
    attempts = []
    errors = []
    for headers in (0, None, 1, 2):
        try:
            raw = _fetch_sheet_gviz("02A_投票速報入力", headers=headers)
            series, debug = parse_turnout_blocks(raw)
            adopted = sum(1 for v in series.values() if v.get("adopted"))
            attempts.append((len(series), adopted, series, debug, headers, raw.shape))
        except Exception as e:
            errors.append(f"headers={headers}: {e}")
    if not attempts:
        raise FetchError(" / ".join(errors) if errors else "02Aを取得できません")
    attempts.sort(key=lambda x: (x[1], x[0]), reverse=True)
    _, _, series, debug, used_headers, shape = attempts[0]
    for row in debug:
        row["GViz方式"] = f"headers={used_headers}; {shape[0]}行×{shape[1]}列"
    return series, debug


@st.cache_data
def load_history():
    import json
    with open(DATA_DIR / "turnout_predict_history.json", encoding="utf-8") as f:
        return json.load(f)


def latest_actual_checkpoint(current_series: dict):
    """全県実績として採用された最後の時刻ラベルを返す（最終を除く）。無ければNone。"""
    latest = None
    for label in CHECKPOINTS:
        entry = current_series.get(label)
        if entry and entry.get("adopted") and entry.get("rate") is not None:
            latest = label
    return latest


def is_final_confirmed(current_series: dict) -> bool:
    """最終ブロックが41市町村そろって正式採用されているかどうか。"""
    entry = current_series.get(FINAL_LABEL)
    return bool(entry and entry.get("adopted") and entry.get("rate") is not None)


def compute_prediction(current_series: dict, history: dict):
    latest = latest_actual_checkpoint(current_series)
    if latest is None:
        return None

    current_rate_now = current_series[latest]["rate"]

    lifts_final = {}
    for key, h in history.items():
        cp = h["checkpoints"].get(latest)
        if cp is None:
            continue
        lifts_final[key] = h["final"] - h["early_equiv_rate"] - cp

    if not lifts_final:
        return None

    weight_sum = sum(history[k]["weight"] for k in lifts_final)
    weighted_lift_final = sum(history[k]["weight"] * lifts_final[k] for k in lifts_final) / weight_sum

    predicted_final = CURRENT_EARLY_EQUIV_RATE + current_rate_now + weighted_lift_final

    # 参考レンジ：台風の影響で特殊値になりやすい2018年（低ウェイト）を除いた
    # 3選挙の上積み幅を採用する。
    normal_lifts = [lifts_final[k] for k in lifts_final if k != "2018"]
    if normal_lifts:
        range_lo = CURRENT_EARLY_EQUIV_RATE + current_rate_now + min(normal_lifts)
        range_hi = CURRENT_EARLY_EQUIV_RATE + current_rate_now + max(normal_lifts)
    else:
        range_lo = range_hi = predicted_final

    # 中間の未来時点（最終より前）は、当日票のみの伸び幅（期日前調整不要）を
    # 過去選挙の同区間の伸びから加重平均して延長する。
    future_points = {}
    remaining = [c for c in CHECKPOINTS if CHECKPOINTS.index(c) > CHECKPOINTS.index(latest)]
    for s in remaining:
        deltas = {}
        for key, h in history.items():
            cp_t = h["checkpoints"].get(latest)
            cp_s = h["checkpoints"].get(s)
            if cp_t is None or cp_s is None:
                continue
            deltas[key] = cp_s - cp_t
        if not deltas:
            continue
        wsum = sum(history[k]["weight"] for k in deltas)
        weighted_delta = sum(history[k]["weight"] * deltas[k] for k in deltas) / wsum
        future_points[s] = current_rate_now + weighted_delta
    future_points[FINAL_LABEL] = predicted_final

    return {
        "latest": latest,
        "current_rate_now": current_rate_now,
        "predicted_final": predicted_final,
        "range_lo": range_lo,
        "range_hi": range_hi,
        "weighted_lift_final": weighted_lift_final,
        "future_points": future_points,
    }


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
.predict-card { background:#111; color:#fff; border-radius:6px; padding:26px 20px; text-align:center; margin-bottom:16px; }
.predict-label { font-size:.85rem; letter-spacing:.08em; color:#bbb; font-weight:700; }
.predict-main { font-family:Georgia,"Yu Mincho",serif; font-size:3.4rem; font-weight:800; margin:4px 0; }
.sub-stat-row { display:flex; gap:14px; justify-content:center; flex-wrap:wrap; margin-top:14px; }
.sub-stat { background:#1e1e1e; border-radius:5px; padding:10px 18px; min-width:140px; }
.sub-stat-label { font-size:.74rem; color:#999; }
.sub-stat-value { font-size:1.25rem; font-weight:800; margin-top:2px; }
.note-box { background:#f7f7f7; border:1px solid #ddd; padding:10px 13px; font-size:.86rem; color:#666; border-radius:5px; margin-top:14px; }
@media(max-width:800px){
  .block-container{padding-left:.7rem;padding-right:.7rem;padding-top:.6rem !important;}
  .predict-main{font-size:2.3rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_turnout", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 投票率予測</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)

if st_autorefresh is not None:
    st_autorefresh(interval=15 * 1000, limit=None, key="turnout-predict-autorefresh")

st.markdown('<div class="page-title">沖縄県知事選　投票率予測</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="deck">当日の中間投票率、過去2回の知事選、直近の参院選・衆院選と比較し、最終投票率を予測します。</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)

history = load_history()

fetch_error = None
try:
    current_series, debug_rows = load_current_timeseries()
    st.session_state["turnout_series_cache"] = (current_series, debug_rows)
except Exception as e:
    fetch_error = str(e)
    cached = st.session_state.get("turnout_series_cache")
    current_series, debug_rows = cached if cached else (None, [])

if current_series is None:
    st.error("投票率データを取得できません。しばらくしてから再読み込みしてください。"
             + (f"\n\n詳細: {fetch_error}" if fetch_error else ""))
    st.stop()
if fetch_error:
    st.warning("直近のデータ取得に失敗したため、前回正常取得できたデータを表示しています。")


def _render_diagnostics(expanded):
    with st.expander("読み取り診断", expanded=expanded):
        st.caption(f"接続先スプレッドシートID: {SHEET_ID}")
        if not debug_rows:
            st.write("「02A_投票速報入力」シートの中に、投票速報のタイトル行が1つも見つかりませんでした。シート名・タブ構成をご確認ください。")
        else:
            st.dataframe(pd.DataFrame(debug_rows), hide_index=True, use_container_width=True)


final_done = is_final_confirmed(current_series)
pred = None if final_done else compute_prediction(current_series, history)

if not final_done and pred is None:
    st.info("まだ全県の投票率実績が入力されていません。10:00の速報が41市町村そろうと予測が始まります。")
    _render_diagnostics(expanded=True)
    st.stop()

if final_done:
    final_rate = current_series[FINAL_LABEL]["rate"]
    st.markdown(
        f"""
<div class="predict-card">
  <div class="predict-label">最終投票率</div>
  <div class="predict-main">{final_rate:.2f}%</div>
  <div class="sub-stat-row">
    <div class="sub-stat"><div class="sub-stat-label">状態</div><div class="sub-stat-value">確定</div></div>
    <div class="sub-stat"><div class="sub-stat-label">前回2022年知事選 最終</div><div class="sub-stat-value">{history['2022']['final']:.2f}%</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption("県選管の最終速報（41市町村すべて）が出そろいました。以降は予測ではなく確定値です。")
else:
    st.markdown(
        f"""
<div class="predict-card">
  <div class="predict-label">最終投票率予測</div>
  <div class="predict-main">{pred['predicted_final']:.1f}%</div>
  <div class="sub-stat-row">
    <div class="sub-stat"><div class="sub-stat-label">想定レンジ</div><div class="sub-stat-value">{pred['range_lo']:.1f}%〜{pred['range_hi']:.1f}%</div></div>
    <div class="sub-stat"><div class="sub-stat-label">{pred['latest']}現在（当日票）</div><div class="sub-stat-value">{pred['current_rate_now']:.2f}%</div></div>
    <div class="sub-stat"><div class="sub-stat-label">前回2022年知事選 最終</div><div class="sub-stat-value">{history['2022']['final']:.2f}%</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(
        f"予測は「今回の期日前投票相当率（{CURRENT_EARLY_EQUIV_RATE:.2f}%）＋{pred['latest']}現在の当日投票率＋"
        "過去選挙から推定した以降の当日投票の上積み」の合計です。確定値ではなく予測値です。"
    )

_render_diagnostics(expanded=False)

# ---------------- chart ----------------
x_labels = CHECKPOINTS + [FINAL_LABEL]
fig = go.Figure()

hist_colors = {"2018": "#C9A227", "2022": "#7A7A7A", "2025SEN": "#3E8E7E", "2026HR": "#8A6FB0"}
for key, h in history.items():
    ys = [h["checkpoints"].get(c) for c in CHECKPOINTS] + [h["final"]]
    fig.add_trace(go.Scatter(
        x=x_labels, y=ys, mode="lines+markers", name=h["label"],
        line=dict(color=hist_colors.get(key, "#999"), width=1.6),
        marker=dict(size=5), opacity=0.75,
        hovertemplate="%{x}<br>" + h["label"] + "：%{y:.2f}%<extra></extra>",
    ))

# 今回：実績（実線）。最終が確定していれば最終点まで実績として含める
actual_x, actual_y = [], []
for c in CHECKPOINTS:
    entry = current_series.get(c)
    if entry and entry.get("rate") is not None:
        actual_x.append(c); actual_y.append(entry["rate"])
if final_done:
    actual_x.append(FINAL_LABEL)
    actual_y.append(current_series[FINAL_LABEL]["rate"])
fig.add_trace(go.Scatter(
    x=actual_x, y=actual_y, mode="lines+markers+text", name="2026年知事選（今回・実績）",
    line=dict(color=RED, width=4), marker=dict(size=9, color=RED),
    text=[f"{y:.2f}%" for y in actual_y], textposition="top center",
    textfont=dict(size=12, color=RED, family="Meiryo, Yu Gothic, sans-serif"),
    hovertemplate="%{x}<br>今回：%{y:.2f}%<extra></extra>",
))

if final_done:
    fig.add_trace(go.Scatter(
        x=[FINAL_LABEL], y=[actual_y[-1]], mode="markers+text", name="確定",
        marker=dict(size=16, color=RED, symbol="diamond", line=dict(color="white", width=1.5)),
        text=[f"確定 {actual_y[-1]:.2f}%"], textposition="top center",
        textfont=dict(size=13, color=RED, family="Meiryo, Yu Gothic, sans-serif"),
        hoverinfo="skip", showlegend=False,
    ))
else:
    # 今回：予測（点線）。最新実績点から始めて未来点へつなぐ
    pred_x = [pred["latest"]] + list(pred["future_points"].keys())
    pred_y = [pred["current_rate_now"]] + list(pred["future_points"].values())
    fig.add_trace(go.Scatter(
        x=pred_x, y=pred_y, mode="lines+markers+text", name="2026年知事選（今回・予測）",
        line=dict(color=RED, width=3, dash="dot"),
        marker=dict(size=[6] * (len(pred_x) - 1) + [14], color=RED,
                    symbol=["circle"] * (len(pred_x) - 1) + ["diamond"]),
        text=[""] * (len(pred_x) - 1) + [f"予測 {pred_y[-1]:.1f}%"],
        textposition="top center",
        textfont=dict(size=13, color=RED, family="Meiryo, Yu Gothic, sans-serif"),
        hovertemplate="%{x}（予測）<br>%{y:.2f}%<extra></extra>",
    ))

fig.update_layout(
    height=480, margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="white", plot_bgcolor="white",
    xaxis=dict(categoryorder="array", categoryarray=x_labels, showgrid=False),
    yaxis=dict(title="投票率（%）", showgrid=True, gridcolor="#eee", ticksuffix="%"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(size=11, family="Meiryo, Yu Gothic, sans-serif")),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

st.markdown(
    """
<div class="note-box">
※10:00〜19:30の中間投票率は当日投票分です。「最終」には期日前投票・不在者投票等が含まれるため、
19:30から最終にかけて数値が大きく上昇します（19:30以降に急に多くの人が投票したという意味ではありません）。
</div>
""",
    unsafe_allow_html=True,
)

if not final_done:
    with st.expander("予測の根拠（過去選挙ごとの内訳）", expanded=False):
        rows = []
        for key, h in history.items():
            cp = h["checkpoints"].get(pred["latest"])
            lift = None if cp is None else h["final"] - h["early_equiv_rate"] - cp
            rows.append({
                "選挙": h["label"],
                "ウェイト": f"{h['weight']*100:.0f}%",
                f"{pred['latest']}投票率": "―" if cp is None else f"{cp:.2f}%",
                "期日前投票相当率": f"{h['early_equiv_rate']:.2f}%",
                "最終投票率": f"{h['final']:.2f}%",
                f"{pred['latest']}以降の上積み": "―" if lift is None else f"{lift:.2f}pt",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption(
            f"今回の期日前投票相当率＝期日前投票者数{CURRENT_EARLY_VOTERS:,}人 ÷ 当日有権者数{CURRENT_ELECTORATE:,}人 ＝ "
            f"{CURRENT_EARLY_EQUIV_RATE:.4f}%。加重平均した上積みは{pred['weighted_lift_final']:.4f}ptです。"
        )
