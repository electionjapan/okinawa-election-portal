
from pathlib import Path
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="沖縄選挙ポータル",
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
.portal-card-history { border-top-color:#1675B9; }
.portal-card-matrix { border-top-color:#222; }
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

    st.markdown('<div class="portal-kicker">OKINAWA ELECTION PORTAL · v0.9.16 · NEW MAP</div>', unsafe_allow_html=True)
    st.markdown('<div class="portal-title">沖縄選挙ポータル</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="portal-deck">沖縄の選挙を、開票速報と過去の確定結果の2つの入口から見るためのポータルです。</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="portal-rule"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown(
            """
<div class="portal-card portal-card-live">
  <div class="portal-card-title">開票速報</div>
  <div class="portal-card-copy">
    開票中の得票、リード幅、推定残票、過去選挙からの保革シフトを追う速報画面。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("開票速報を見る", key="home_live", type="primary", use_container_width=True):
            go("live")

    with c2:
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

    with c3:
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

    st.markdown(
        '<div class="portal-foot">Okinawa Election Portal — v0.9.16</div>',
        unsafe_allow_html=True,
    )

page = st.session_state["portal_page"]

if page == "home":
    render_home()
elif page == "live":
    exec(compile((APP_DIR / "live_results.py").read_text(encoding="utf-8"), "live_results.py", "exec"))
elif page == "history":
    exec(compile((APP_DIR / "historical_results.py").read_text(encoding="utf-8"), "historical_results.py", "exec"))
elif page == "matrix":
    exec(compile((APP_DIR / "matrix_results.py").read_text(encoding="utf-8"), "matrix_results.py", "exec"))
else:
    st.session_state["portal_page"] = "home"
    st.rerun()
