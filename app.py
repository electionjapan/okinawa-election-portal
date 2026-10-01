
from pathlib import Path
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="選挙データポータル",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "portal_page" not in st.session_state:
    st.session_state["portal_page"] = "home"

def go(page):
    st.session_state["portal_page"] = page
    st.rerun()

def render_home():
    st.markdown(
        """
<style>
html, body, [class*="css"] {
    font-family:"Meiryo","Yu Gothic",system-ui,sans-serif;
    color:#292929;
}
.block-container {
    max-width:1180px;
    padding-top:1.6rem;
    padding-bottom:5rem;
}
#MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stAppViewContainer"] { padding-top: 0 !important; }
.portal-kicker {
    font-size:.78rem;
    font-weight:800;
    letter-spacing:.11em;
    color:#666;
    text-align:center;
}
.portal-title {
    font-family:Georgia,"Yu Mincho",serif;
    font-size:3.15rem;
    font-weight:800;
    letter-spacing:-.035em;
    line-height:1.05;
    text-align:center;
    margin-top:.45rem;
}
.portal-deck {
    color:#6B6B6B;
    font-size:1rem;
    line-height:1.7;
    text-align:center;
    max-width:720px;
    margin:.8rem auto 2.25rem;
}
.portal-rule {
    border-top:4px solid #111;
    max-width:900px;
    margin:0 auto 2.15rem;
}
.portal-card {
    border:1px solid #D8D8D8;
    border-top:5px solid #222;
    padding:1.5rem 1.55rem 1.2rem;
    min-height:190px;
    background:#fff;
}
.portal-card-live { border-top-color:#C93238; }
.portal-card-turnout { border-top-color:#B8860B; }
.portal-card-history { border-top-color:#1675B9; }
.portal-card-matrix { border-top-color:#222; }
.portal-card-shizuoka { border-top-color:#5A7247; }
.portal-card-realmap { border-top-color:#1E6E5C; }
.portal-card-title {
    font-family:Georgia,"Yu Mincho",serif;
    font-size:1.65rem;
    font-weight:800;
    margin-bottom:.45rem;
}
.portal-card-copy {
    color:#666;
    line-height:1.65;
    font-size:.93rem;
    min-height:62px;
}
.portal-foot {
    text-align:center;
    color:#888;
    font-size:.8rem;
    margin-top:2rem;
}
div[data-testid="stButton"] > button {
    min-height:3.15rem;
    font-weight:800;
    font-size:1rem;
    border-radius:3px;
}
@media(max-width:700px) {
    .block-container { padding-top:1.2rem; }
    .portal-title { font-size:2.3rem; }
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="portal-kicker">ELECTION DATA PORTAL · v0.10.1</div>', unsafe_allow_html=True)
    st.markdown('<div class="portal-title">選挙データポータル</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="portal-deck">沖縄の選挙アーカイブと、2026年アメリカ中間選挙のリアルタイム開票を一つの入口から見るポータルです。</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="portal-rule"></div>', unsafe_allow_html=True)

    st.markdown("""
<div class="portal-card" style="border-top-color:#1F4E79;min-height:150px;margin-bottom:1.4rem;">
  <div class="portal-card-title">🇺🇸 2026 アメリカ中間選挙</div>
  <div class="portal-card-copy">civicAPIから上院・下院・知事選を取得。上院100議席ボード、MY WATCH、票差・開票率、当確監視、レース詳細に対応。</div>
</div>
""", unsafe_allow_html=True)
    if st.button("US MIDTERMSを開く", key="home_us", type="primary", use_container_width=True):
        go("us")

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown(
            """
<div class="portal-card portal-card-live">
  <div class="portal-card-title">沖縄知事選 開票速報【更新終了】</div>
  <div class="portal-card-copy">
    2026年9月13日の運用を終了。Googleスプレッドシートからのデータ取得は停止済みです。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("更新終了の案内", key="home_live", use_container_width=True):
            go("okinawa_closed")

    with c2:
        st.markdown(
            """
<div class="portal-card portal-card-turnout">
  <div class="portal-card-title">沖縄 投票率予測【更新終了】</div>
  <div class="portal-card-copy">
    リアルタイム取得は終了。投票速報シートへのアクセスは行いません。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("更新終了の案内", key="home_turnout", use_container_width=True):
            go("okinawa_closed")

    with c3:
        st.markdown(
            """
<div class="portal-card portal-card-history">
  <div class="portal-card-title">過去の選挙結果</div>
  <div class="portal-card-copy">
    過去の全県選挙を切り替えながら、市町村別結果や保革マージンの変化を比較するアーカイブ。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("過去の選挙結果を見る", key="home_history", use_container_width=True):
            go("history")

    c4, c5, c6 = st.columns(3, gap="large")

    with c4:
        st.markdown(
            """
<div class="portal-card portal-card-matrix">
  <div class="portal-card-title">41市町村 保守寄り？革新より？</div>
  <div class="portal-card-copy">
    知事選・参院選・衆院選をまたいで、市町村ごとの勝差を一覧表と地図で比較。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("一覧で比較する", key="home_matrix", use_container_width=True):
            go("matrix")

    with c5:
        st.markdown(
            """
<div class="portal-card portal-card-shizuoka">
  <div class="portal-card-title">静岡県 過去の選挙</div>
  <div class="portal-card-copy">
    1974年知事選をはじめ、静岡県の過去の選挙を市町村別・郡別の地図で見る。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("静岡を見る", key="home_shizuoka", use_container_width=True):
            go("shizuoka")

    with c6:
        st.markdown(
            """
<div class="portal-card portal-card-realmap">
  <div class="portal-card-title">沖縄 開票マップ【更新終了】</div>
  <div class="portal-card-copy">
    リアルタイム取得は終了。Googleスプレッドシートへのアクセスは行いません。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("更新終了の案内", key="home_realmap", use_container_width=True):
            go("okinawa_closed")

    st.markdown(
        '<div class="portal-foot">Election Data Portal — v0.10.1</div>',
        unsafe_allow_html=True,
    )

page = st.session_state["portal_page"]

def render_okinawa_closed():
    if st.button("← ポータルTOP", key="closed_back"):
        go("home")
    st.title("沖縄県知事選 2026 — 更新終了")
    st.info("2026年9月13日の選挙運用は終了しました。リアルタイム用Googleスプレッドシートからのデータ取得・自動更新は停止しています。")
    st.markdown("過去選挙の確定データ、市町村マトリクス、静岡県の過去選挙ページは引き続きローカルJSONのみで閲覧できます。")

if page == "home":
    render_home()
elif page == "us":
    exec(compile((APP_DIR / "us_midterms.py").read_text(encoding="utf-8"), "us_midterms.py", "exec"))
elif page in {"live", "turnout", "realmap", "okinawa_closed"}:
    # 重要: 沖縄ライブ用ファイルは実行しない。これによりGoogle Sheetsへのアクセスも発生しない。
    render_okinawa_closed()
elif page == "history":
    exec(compile((APP_DIR / "historical_results.py").read_text(encoding="utf-8"), "historical_results.py", "exec"))
elif page == "matrix":
    exec(compile((APP_DIR / "matrix_results.py").read_text(encoding="utf-8"), "matrix_results.py", "exec"))
elif page == "shizuoka":
    exec(compile((APP_DIR / "shizuoka_results.py").read_text(encoding="utf-8"), "shizuoka_results.py", "exec"))
else:
    st.session_state["portal_page"] = "home"
    st.rerun()
