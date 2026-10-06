"""
参院比例 個人票分析 ページ

全国市区町村・政令市行政区別の2022/2025年参議院比例代表の個人票を分析する。
既存ポータルの他ページとは独立したモジュール(sangiin_pr_data.py)からデータ・指標を
読み込み、地図や表を描画する。既存の app.py ルーター・他ページのコードには影響しない。
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import sangiin_pr_data as spd

APP_DIR_SP = spd.APP_DIR

# ---------------------------------------------------------------------------
# スタイル・ナビゲーション(既存ポータルのデザイン言語に合わせる)
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
html, body, [class*="css"] { font-family:"Meiryo","Yu Gothic",system-ui,sans-serif; color:#292929; }
.block-container { max-width:1320px; padding-top:.6rem; padding-bottom:4rem; }
.portal-nav-spacer { height:.15rem; }
.portal-breadcrumb { color:#777; font-size:.82rem; padding-top:.68rem; white-space:nowrap; }
#MainMenu, footer, header[data-testid="stHeader"] { display:none !important; }
div[data-testid="stAppViewContainer"] { padding-top:0 !important; }
.page-title { font-family:Georgia,"Yu Mincho",serif; font-size:2.05rem; font-weight:800; margin-top:.2rem; }
.deck { color:#6B6B6B; font-size:.92rem; margin-top:.2rem; }
.top-rule { border-top:4px solid #111; margin:10px 0 14px; }
.sp-stat-strip { display:flex; gap:22px; flex-wrap:wrap; font-size:.9rem; color:#333; margin:.3rem 0 .9rem; }
.sp-stat-strip strong { font-size:1.15rem; display:block; }
.sp-card { border:1px solid #DDD; border-left:5px solid #222; padding:.9rem 1.1rem; background:#fafafa; margin-bottom:.8rem; }
.sp-badge-special { background:#eee; color:#555; border:1px solid #ccc; font-size:.72rem; padding:1px 6px; border-radius:3px; margin-left:.4rem; }
.sp-section-title { font-weight:800; font-size:1.08rem; margin:1.1rem 0 .4rem; border-left:5px solid #222; padding-left:.5rem; }
.sp-footnote { color:#888; font-size:.74rem; margin-top:1.2rem; line-height:1.7; border-top:1px solid #eee; padding-top:.6rem; }
@media(max-width:800px){
  .block-container{padding-left:.7rem;padding-right:.7rem;padding-top:.6rem !important;}
  .page-title{font-size:1.35rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

nav_back, nav_label = st.columns([1.7, 6.3], gap="small")
with nav_back:
    if st.button("← トップへ戻る", key="portal_back_sangiin_pr", use_container_width=True):
        st.session_state["portal_page"] = "home"
        st.rerun()
with nav_label:
    st.markdown('<div class="portal-breadcrumb">沖縄選挙ポータル ／ 参院比例 個人票分析</div>', unsafe_allow_html=True)
st.markdown('<div class="portal-nav-spacer"></div>', unsafe_allow_html=True)

st.markdown('<div class="page-title">参院比例 個人票分析</div>', unsafe_allow_html=True)
st.markdown('<div class="deck">全国市区町村・政令市行政区別｜2022 / 2025</div>', unsafe_allow_html=True)
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)


def fmt_votes(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "―"
    if abs(f - round(f)) < 1e-9:
        return f"{round(f):,}"
    return f"{f:,.3f}"


def fmt_pct(v, digits=1) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "―"
    return f"{v*100:.{digits}f}%"


def fmt_num(v, digits=1) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "―"
    return f"{v:.{digits}f}"


def decimal_csv(df: pd.DataFrame, decimal_cols: dict) -> bytes:
    """decimal_cols = {出力列名: Decimal列} を文字列のまま書き出し、小数桁を保持する。"""
    out = df.copy()
    for col, series in decimal_cols.items():
        out[col] = series.astype(str)
    return out.to_csv(index=False).encode("utf-8-sig")


# ---------------------------------------------------------------------------
# 年セレクタ(ページ共通。タブEは両年を使うため別途内部で両年を読む)
# ---------------------------------------------------------------------------
if "sp_pending_tab" in st.session_state:
    st.session_state["sp_tab_radio"] = st.session_state.pop("sp_pending_tab")

TAB_OPTIONS = ["A. 概況", "B. 候補者分析", "C. 政党分析", "D. 自治体カルテ", "E. 2022→2025比較"]
active_tab = st.radio("タブ", TAB_OPTIONS, horizontal=True, key="sp_tab_radio", label_visibility="collapsed")

year_col, _sp = st.columns([1.2, 5.0])
with year_col:
    year = st.radio("年", [2025, 2022], horizontal=True, key="sp_year_radio", label_visibility="visible")

st.markdown("")

PARTIES = spd.active_parties(year)


def goto(tab: str, **state):
    st.session_state["sp_pending_tab"] = tab
    for k, v in state.items():
        st.session_state[k] = v
    st.rerun()


# ===========================================================================
# TAB A: 概況
# ===========================================================================
if active_tab == "A. 概況":
    vv = spd.load_valid_votes(year)
    pt = spd.load_party_totals(year)
    total_valid = vv["valid_votes"].apply(float).sum()
    total_party_name = pt["party_name_votes"].apply(float).sum()
    total_candidate = pt["candidate_sum"].apply(float).sum()
    n_parties = pt["party"].nunique()

    st.markdown(
        f"""
<div class="sp-stat-strip">
  <span><strong>{total_valid:,.0f}票</strong>比例有効票(全国)</span>
  <span><strong>{n_parties}党</strong>届出政党数</span>
  <span><strong>{total_party_name:,.0f}票</strong>政党名投票</span>
  <span><strong>{total_candidate:,.0f}票</strong>候補者個人票</span>
  <span><strong>{100*total_candidate/total_valid:.1f}%</strong>個人票比率</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sp-section-title">政党別得票(全国)</div>', unsafe_allow_html=True)
    party_sum = pt.groupby("party")["party_total"].apply(lambda s: float(sum(s))).sort_values(ascending=False)
    bar_df = party_sum.reset_index()
    bar_df.columns = ["party", "votes"]
    fig_bar = px.bar(
        bar_df, x="votes", y="party", orientation="h",
        color="party", color_discrete_map={p: spd.party_color(p) for p in bar_df["party"]},
    )
    fig_bar.update_layout(showlegend=False, height=max(360, 24 * len(bar_df)), yaxis=dict(categoryorder="total ascending"),
                          margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown('<div class="sp-section-title">候補者 個人票 全国TOP20</div>', unsafe_allow_html=True)
    cm = spd.candidates_for(year).head(20).copy()
    cm["national_votes_f"] = cm["national_votes"].astype(float)
    cm_show = cm[["candidate", "party", "national_votes_f"]].rename(
        columns={"candidate": "候補者", "party": "政党", "national_votes_f": "全国個人票"}
    ).reset_index(drop=True)
    cm_show.index = cm_show.index + 1
    st.dataframe(cm_show.style.format({"全国個人票": "{:,.0f}"}), use_container_width=True)

    st.markdown('<div class="sp-section-title">全国マップ(比例有効票)</div>', unsafe_allow_html=True)
    st.caption("候補者・政党を選ぶと指標マップに切り替わります。まずは比例有効票の分布です。")
    geo_master = spd.load_geo_master(year)
    geo_master = geo_master[geo_master["has_election_data"] == 1]
    map_df = geo_master.merge(vv, on="geometry_key", how="left")
    map_df["valid_votes_f"] = map_df["valid_votes"].astype(float)
    map_df["hover"] = map_df.apply(lambda r: f"<b>{r['pref_name']} {r['display_name']}</b><br>比例有効票 {r['valid_votes_f']:,.0f}票", axis=1)
    web_geo = spd.load_web_geojson(year)
    fig_map = spd.build_choropleth_figure(web_geo, map_df, "valid_votes_f", "hover", colorscale="Blues",
                                           colorbar_title="有効票", height=620)
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('<div class="sp-section-title">候補者・市区町村を検索</div>', unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        q = st.text_input("候補者名で検索(部分一致)", key="sp_a_cand_search")
        if q:
            res = spd.search_candidates(year, q)
            if res.empty:
                st.info("該当する候補者が見つかりません。")
            else:
                for _, r in res.head(10).iterrows():
                    label = f"{r['candidate']}({r['party']}) {float(r['national_votes']):,.0f}票"
                    if st.button(label, key=f"sp_a_jump_{r['party']}_{r['candidate_number']}"):
                        goto("B. 候補者分析", sp_sel_year=year, sp_sel_party=r["party"], sp_sel_cnum=r["candidate_number"])
    with s2:
        m_q = st.text_input("市区町村名で検索", key="sp_a_muni_search")
        if m_q:
            gm = spd.load_geo_master(year)
            gm = gm[gm["has_election_data"] == 1]
            hit = gm[gm["display_name"].str.contains(m_q.strip(), na=False)]
            if hit.empty:
                st.info("該当する市区町村が見つかりません。")
            else:
                for _, r in hit.head(10).iterrows():
                    label = f"{r['pref_name']} {r['display_name']}"
                    if st.button(label, key=f"sp_a_jump_m_{r['geometry_key']}"):
                        goto("D. 自治体カルテ", sp_sel_year=year, sp_sel_geometry_key=r["geometry_key"])

# ===========================================================================
# TAB B: 候補者分析(メイン機能)
# ===========================================================================
elif active_tab == "B. 候補者分析":
    st.markdown('<div class="sp-section-title">候補者を選択</div>', unsafe_allow_html=True)

    pending_party = st.session_state.pop("sp_sel_party", None)
    pending_cnum = st.session_state.pop("sp_sel_cnum", None)
    pending_year = st.session_state.pop("sp_sel_year", None)
    if pending_year is not None and pending_year != year:
        # 候補者は年固有のため、遷移元の年に合わせて年ラジオも切り替える
        st.session_state["sp_year_radio"] = pending_year
        st.session_state["sp_sel_party"] = pending_party
        st.session_state["sp_sel_cnum"] = pending_cnum
        st.rerun()

    f1, f2, f3 = st.columns([1.3, 1.6, 1.6])
    with f1:
        party_options = ["(すべて)"] + PARTIES
        default_party_idx = party_options.index(pending_party) if pending_party in party_options else 0
        party_sel = st.selectbox("政党で絞り込み", party_options, index=default_party_idx, key="sp_b_party")
    with f2:
        name_q = st.text_input("候補者名で検索(部分一致)", key="sp_b_name_search")
    with f3:
        party_arg = None if party_sel == "(すべて)" else party_sel
        cand_pool = spd.search_candidates(year, name_q) if name_q else spd.candidates_for(year, party_arg)
        if party_arg and name_q:
            cand_pool = cand_pool[cand_pool["party"] == party_arg]
        if cand_pool.empty:
            st.warning("条件に一致する候補者がいません。")
            st.stop()
        labels = [f"{r['candidate']}({r['party']}) {float(r['national_votes']):,.0f}票" for _, r in cand_pool.iterrows()]
        default_idx = 0
        if pending_cnum is not None:
            for i, (_, r) in enumerate(cand_pool.iterrows()):
                if r["candidate_number"] == pending_cnum and (party_arg is None or r["party"] == party_arg):
                    default_idx = i
                    break
        sel_label = st.selectbox("候補者", labels, index=min(default_idx, len(labels) - 1), key="sp_b_cand_select")
    sel_row = cand_pool.iloc[labels.index(sel_label)]
    sel_party, sel_cnum = sel_row["party"], sel_row["candidate_number"]

    df = spd.candidate_municipality_table(year, sel_party, sel_cnum)
    stats = spd.concentration_stats(df)
    cand_name = df.attrs["candidate_name"]
    national_votes = df.attrs["candidate_national_votes"]

    same_party_all = spd.candidates_for(year, sel_party)
    rank_in_party = int((same_party_all["national_votes"].astype(float) > national_votes).sum()) + 1
    all_cands = spd.candidates_for(year)
    rank_overall = int((all_cands["national_votes"].astype(float) > national_votes).sum()) + 1
    party_share_of_national = national_votes / df.attrs["party_candidate_votes_national"] if df.attrs["party_candidate_votes_national"] else None

    top_pref_row = df.groupby("pref_name")["candidate_votes_f"].sum().sort_values(ascending=False)
    top_pref = top_pref_row.index[0] if len(top_pref_row) else "―"
    top_muni_row = df.sort_values("candidate_votes_f", ascending=False).iloc[0] if len(df) else None

    special_badge = ""
    if int(sel_row.get("candidate_is_special", 0)) == 1:
        special_badge = '<span class="sp-badge-special">特定枠(個人票集計から除外)</span>'

    st.markdown(
        f"""
<div class="sp-card">
  <div style="font-size:1.3rem;font-weight:800;">{cand_name}{special_badge}</div>
  <div style="color:#666;margin-bottom:.5rem;">{sel_party}・{year}年</div>
  <div class="sp-stat-strip">
    <span><strong>{national_votes:,.0f}票</strong>全国個人票</span>
    <span><strong>{rank_in_party}位</strong>党内順位</span>
    <span><strong>{rank_overall}位</strong>全候補者中順位</span>
    <span><strong>{fmt_pct(party_share_of_national)}</strong>党内候補者票シェア</span>
    <span><strong>{top_pref}</strong>最多獲票都道府県</span>
    <span><strong>{(top_muni_row['pref_name']+' '+top_muni_row['display_name']) if top_muni_row is not None else '―'}</strong>最多獲票市区町村</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sp-section-title">全国マップ(指標切替)</div>', unsafe_allow_html=True)
    indicator = st.radio(
        "指標",
        ["個人票数", "比例有効票に占める個人票率", "党内候補者占有率", "全国票寄与率", "地域偏在指数"],
        horizontal=True, key="sp_b_indicator",
    )
    indicator_map = {
        "個人票数": ("candidate_votes_f", "YlOrRd", None, None, None, "票"),
        "比例有効票に占める個人票率": ("candidate_valid_share", "YlOrRd", None, None, None, "比率"),
        "党内候補者占有率": ("candidate_within_party_share", "YlOrRd", None, None, None, "比率"),
        "全国票寄与率": ("national_contribution", "YlOrRd", None, None, None, "比率"),
        "地域偏在指数": ("regional_concentration_index", "RdBu", 100, None, None, "指数(100=全国平均)"),
    }
    col, scale, zmid, zmin, zmax, cbar_title = indicator_map[indicator]
    plot_df = df.dropna(subset=[col]).copy() if col != "candidate_votes_f" else df.copy()
    plot_df["hover"] = plot_df.apply(spd.hover_text_candidate, axis=1)
    web_geo = spd.load_web_geojson(year)
    fig_map = spd.build_choropleth_figure(web_geo, plot_df, col, "hover", colorscale=scale,
                                           zmid=zmid, colorbar_title=cbar_title, height=640)
    st.plotly_chart(fig_map, use_container_width=True)
    pref_filter = st.selectbox("都道府県で拡大(任意)", ["(全国)"] + sorted(df["pref_name"].unique().tolist()), key="sp_b_pref_zoom")
    if pref_filter != "(全国)":
        pref_code = df[df["pref_name"] == pref_filter]["pref_code"].iloc[0]
        detail = spd.load_detail_geojson(year, pref_code)
        if detail:
            sub = df[df["pref_code"] == pref_code].dropna(subset=[col]) if col != "candidate_votes_f" else df[df["pref_code"] == pref_code]
            sub = sub.copy()
            sub["hover"] = sub.apply(spd.hover_text_candidate, axis=1)
            fig_detail = spd.build_choropleth_figure(detail, sub, col, "hover", colorscale=scale, zmid=zmid,
                                                       colorbar_title=cbar_title, height=560)
            fig_detail.update_layout(map=dict(style="open-street-map"))
            st.plotly_chart(fig_detail, use_container_width=True)

    st.markdown('<div class="sp-section-title">集票構造(N50/N80・HHI・Gini・正規化エントロピー)</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("N50", stats["n50"] if stats["n50"] else "―", help="全国票の50%に達するまでに必要な最少市区町村数")
    m2.metric("N80", stats["n80"] if stats["n80"] else "―", help="全国票の80%に達するまでに必要な最少市区町村数")
    m3.metric("HHI", fmt_num(stats["hhi"], 1) if stats["hhi"] is not None else "―")
    m4.metric("Gini", fmt_num(stats["gini"], 3) if stats["gini"] is not None else "―")
    m5.metric("正規化エントロピー", fmt_num(stats["entropy"], 3) if stats["entropy"] is not None else "―",
              help="0に近いほど集中、1に近いほど分散")

    curve = spd.cumulative_curve(df)
    if not curve.empty:
        fig_curve = px.line(curve, x="n", y="pct", labels={"n": "上位からの市区町村数", "pct": "全国票に占める累積%"})
        fig_curve.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_curve, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**得票数 TOP20**")
        t1 = df.sort_values("candidate_votes_f", ascending=False).head(20)[["pref_name", "display_name", "candidate_votes_f"]]
        st.dataframe(t1.rename(columns={"pref_name": "都道府県", "display_name": "市区町村", "candidate_votes_f": "個人票"})
                     .reset_index(drop=True).style.format({"個人票": "{:,.0f}"}), use_container_width=True, height=380)
    with c2:
        st.markdown("**個人票率 TOP20**")
        t2 = df.dropna(subset=["candidate_valid_share"]).sort_values("candidate_valid_share", ascending=False).head(20)
        t2 = t2[["pref_name", "display_name", "candidate_valid_share"]]
        st.dataframe(t2.rename(columns={"pref_name": "都道府県", "display_name": "市区町村", "candidate_valid_share": "個人票率"})
                     .reset_index(drop=True).style.format({"個人票率": "{:.2%}"}), use_container_width=True, height=380)
    with c3:
        st.markdown("**地域偏在指数 TOP20**")
        t3 = df.dropna(subset=["regional_concentration_index"]).sort_values("regional_concentration_index", ascending=False).head(20)
        t3 = t3[["pref_name", "display_name", "regional_concentration_index"]]
        st.dataframe(t3.rename(columns={"pref_name": "都道府県", "display_name": "市区町村", "regional_concentration_index": "偏在指数"})
                     .reset_index(drop=True).style.format({"偏在指数": "{:.0f}"}), use_container_width=True, height=380)

    st.markdown('<div class="sp-section-title">都道府県別 寄与割合</div>', unsafe_allow_html=True)
    pref_contrib = df.groupby("pref_name")["candidate_votes_f"].sum().sort_values(ascending=False)
    pref_contrib = pref_contrib[pref_contrib > 0].reset_index()
    pref_contrib.columns = ["pref_name", "votes"]
    fig_pref = px.bar(pref_contrib.head(15), x="votes", y="pref_name", orientation="h")
    fig_pref.update_layout(yaxis=dict(categoryorder="total ascending"), height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_pref, use_container_width=True)

    st.markdown('<div class="sp-section-title">地方 → 都道府県 → 自治体(票構成)</div>', unsafe_allow_html=True)
    tree_df = df[df["candidate_votes_f"] > 0].copy()
    if not tree_df.empty:
        fig_tree = px.treemap(
            tree_df, path=["region", "pref_name", "display_name"], values="candidate_votes_f",
            color="region", color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_tree.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("この候補者の個人票データがありません。")

    export_df = df[["pref_name", "display_name", "region", "admin_type"]].copy()
    export_df["候補者個人票"] = df["candidate_votes"]
    export_df["比例有効票"] = df["valid_votes"]
    export_df["個人票率"] = df["candidate_valid_share"]
    export_df["党内占有率"] = df["candidate_within_party_share"]
    export_df["全国票寄与率"] = df["national_contribution"]
    export_df["地域偏在指数"] = df["regional_concentration_index"]
    csv_bytes = decimal_csv(export_df, {"候補者個人票": df["candidate_votes"], "比例有効票": df["valid_votes"]})
    st.download_button("この候補者の自治体別データをCSVでダウンロード", data=csv_bytes,
                        file_name=f"sangiin_pr_{year}_{sel_party}_{cand_name}.csv", mime="text/csv")

# ===========================================================================
# TAB C: 政党分析
# ===========================================================================
elif active_tab == "C. 政党分析":
    pending_party = st.session_state.pop("sp_sel_party_c", None)
    default_idx = PARTIES.index(pending_party) if pending_party in PARTIES else 0
    party = st.selectbox("政党を選択", PARTIES, index=default_idx, key="sp_c_party")

    pdf = spd.party_municipality_table(year, party)
    total_pt = pdf["party_total_f"].sum()
    total_valid_all = spd.load_valid_votes(year)["valid_votes"].apply(float).sum()
    total_cs = pdf["candidate_sum"].apply(float).sum()
    total_pn = pdf["party_name_votes"].apply(float).sum()

    st.markdown(
        f"""
<div class="sp-stat-strip">
  <span><strong>{total_pt:,.0f}票</strong>党全体の得票(party_total)</span>
  <span><strong>{total_pn:,.0f}票</strong>政党名投票</span>
  <span><strong>{total_cs:,.0f}票</strong>候補者個人票合計</span>
  <span><strong>{fmt_pct(total_pt/total_valid_all) if total_valid_all else '―'}</strong>全国得票シェア</span>
  <span><strong>{fmt_pct(total_pn/total_pt) if total_pt else '―'}</strong>政党名投票比率</span>
  <span><strong>{fmt_pct(total_cs/total_pt) if total_pt else '―'}</strong>候補者票比率</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sp-section-title">候補者別 全国順位</div>', unsafe_allow_html=True)
    cand_rank = spd.candidates_for(year, party).copy()
    cand_rank["national_votes_f"] = cand_rank["national_votes"].astype(float)
    cand_rank = cand_rank[["candidate", "national_votes_f"]].reset_index(drop=True)
    cand_rank.index = cand_rank.index + 1
    st.dataframe(cand_rank.rename(columns={"candidate": "候補者", "national_votes_f": "全国個人票"})
                 .style.format({"全国個人票": "{:,.0f}"}), use_container_width=True)

    special = spd.special_candidates_for_party(year, party)
    if not special.empty:
        st.caption("特定枠候補者(個人票集計から除外): " + "、".join(special["candidate"].tolist()))

    st.markdown('<div class="sp-section-title">全国マップ(指標切替)</div>', unsafe_allow_html=True)
    ind_options = ["党全体の得票", "得票シェア", "政党名投票比率", "候補者票比率"]
    other_year = 2022 if year == 2025 else 2025
    if party in spd.active_parties(other_year):
        ind_options.append(f"{year}→{other_year if other_year>year else year}比較(得票シェア差)" if False else "2022→2025スイング(得票シェアpt差)")
    indicator_c = st.radio("指標", ind_options, horizontal=True, key="sp_c_indicator")

    if indicator_c == "2022→2025スイング(得票シェアpt差)":
        pdf25 = spd.party_municipality_table(2025, party)[["geometry_key", "pref_name", "display_name", "party_share"]].rename(columns={"party_share": "share_2025"})
        pdf22 = spd.party_municipality_table(2022, party)[["geometry_key", "party_share"]].rename(columns={"party_share": "share_2022"})
        merged = pdf25.merge(pdf22, on="geometry_key", how="inner")
        merged["diff_pp"] = (merged["share_2025"].fillna(0) - merged["share_2022"].fillna(0)) * 100.0
        merged["hover"] = merged.apply(lambda r: f"<b>{r['pref_name']} {r['display_name']}</b><br>差分 {r['diff_pp']:+.2f}pt", axis=1)
        web_geo25 = spd.load_web_geojson(2025)
        fig_map = spd.build_choropleth_figure(web_geo25, merged, "diff_pp", "hover", colorscale="RdBu", zmid=0,
                                               colorbar_title="pt差", height=620)
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption("2025年の地図境界を基準に表示しています(浜松市・仙台市などの行政区再編は反映済みの年の境界で比較)。")
    else:
        col_map = {"党全体の得票": "party_total_f", "得票シェア": "party_share", "政党名投票比率": "party_name_share", "候補者票比率": "candidate_vote_share"}
        col = col_map[indicator_c]
        plot_df = pdf.dropna(subset=[col]).copy() if col != "party_total_f" else pdf.copy()
        plot_df["hover"] = plot_df.apply(
            lambda r: f"<b>{r['pref_name']} {r['display_name']}</b><br>{indicator_c}: " + (
                f"{r[col]:,.0f}" if col == "party_total_f" else f"{r[col]*100:.2f}%"), axis=1)
        web_geo = spd.load_web_geojson(year)
        scale = "YlOrRd"
        fig_map = spd.build_choropleth_figure(web_geo, plot_df, col, "hover", colorscale=scale,
                                               colorbar_title=indicator_c, height=620)
        st.plotly_chart(fig_map, use_container_width=True)

    export_df = pdf[["pref_name", "display_name", "region", "admin_type"]].copy()
    export_df["党得票"] = pdf["party_total"]
    export_df["政党名投票"] = pdf["party_name_votes"]
    export_df["候補者票合計"] = pdf["candidate_sum"]
    export_df["比例有効票"] = pdf["valid_votes"]
    csv_bytes = decimal_csv(export_df, {"党得票": pdf["party_total"], "政党名投票": pdf["party_name_votes"],
                                          "候補者票合計": pdf["candidate_sum"], "比例有効票": pdf["valid_votes"]})
    st.download_button("この政党の自治体別データをCSVでダウンロード", data=csv_bytes,
                        file_name=f"sangiin_pr_{year}_{party}_party.csv", mime="text/csv")

# ===========================================================================
# TAB D: 自治体カルテ
# ===========================================================================
elif active_tab == "D. 自治体カルテ":
    gm = spd.load_geo_master(year)
    gm = gm[gm["has_election_data"] == 1]

    pending_gkey = st.session_state.pop("sp_sel_geometry_key", None)
    prefs = sorted(gm["pref_name"].unique().tolist())
    default_pref = gm[gm["geometry_key"] == pending_gkey]["pref_name"].iloc[0] if pending_gkey in gm["geometry_key"].values else prefs[0]
    pref_sel = st.selectbox("都道府県", prefs, index=prefs.index(default_pref), key="sp_d_pref")
    munis = gm[gm["pref_name"] == pref_sel].sort_values("display_name")
    muni_labels = munis["display_name"].tolist()
    default_muni_idx = 0
    if pending_gkey in munis["geometry_key"].values:
        default_muni_idx = munis["geometry_key"].tolist().index(pending_gkey)
    muni_sel_label = st.selectbox("市区町村", muni_labels, index=default_muni_idx, key="sp_d_muni")
    gkey = munis[munis["display_name"] == muni_sel_label]["geometry_key"].iloc[0]
    muni_row = munis[munis["geometry_key"] == gkey].iloc[0]

    vv = spd.load_valid_votes(year)
    valid_votes_m = vv[vv["geometry_key"] == gkey]["valid_votes"]
    valid_votes_m = float(valid_votes_m.iloc[0]) if not valid_votes_m.empty else 0.0

    st.markdown(
        f"""
<div class="sp-card">
  <div style="font-size:1.25rem;font-weight:800;">{muni_row['pref_name']} {muni_row['display_name']}</div>
  <div class="sp-stat-strip">
    <span><strong>{valid_votes_m:,.0f}票</strong>比例有効票</span>
    <span><strong>{muni_row['region']}</strong>地方</span>
    <span><strong>{muni_row['admin_type']}</strong>行政区分</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sp-section-title">政党別得票・得票率</div>', unsafe_allow_html=True)
    pr = spd.municipality_party_ranking(year, gkey)
    pr_show = pr[["party", "party_total_f", "share", "party_name_votes_f", "candidate_sum_f"]].rename(
        columns={"party": "政党", "party_total_f": "党得票", "share": "得票率", "party_name_votes_f": "政党名投票",
                 "candidate_sum_f": "候補者票合計"}
    ).reset_index(drop=True)
    pr_show.index = pr_show.index + 1
    st.dataframe(pr_show.style.format({"党得票": "{:,.0f}", "得票率": "{:.2%}", "政党名投票": "{:,.0f}", "候補者票合計": "{:,.0f}"}),
                 use_container_width=True)

    st.markdown('<div class="sp-section-title">候補者個人票ランキング(全政党横断)</div>', unsafe_allow_html=True)
    cr = spd.municipality_candidate_ranking(year, gkey)

    # 党内占有率・全国票寄与率・地域偏在指数(このページの標準指標)を候補者ごとに付与
    cm = spd.load_candidate_master()
    cm_y = cm[(cm["year"] == year)][["party", "candidate_number", "national_votes"]].copy()
    cm_y["national_votes_f"] = cm_y["national_votes"].astype(float)
    pt_all = spd.load_party_totals(year)
    party_cs_national = pt_all.groupby("party")["candidate_sum"].apply(lambda s: float(sum(s)))
    party_cs_here = pr.set_index("party")["candidate_sum_f"]

    def rci_for(row):
        p = row["party"]
        cs_here = party_cs_here.get(p, 0.0)
        if cs_here <= 0:
            return None
        local_share = row["votes_f"] / cs_here
        nat_row = cm_y[(cm_y["party"] == p) & (cm_y["candidate_number"] == row["candidate_number"])]
        if nat_row.empty:
            return None
        nat_votes = nat_row["national_votes_f"].iloc[0]
        cs_nat = party_cs_national.get(p, 0.0)
        if cs_nat <= 0 or nat_votes <= 0:
            return None
        national_share = nat_votes / cs_nat
        if national_share == 0:
            return None
        return (local_share / national_share) * 100.0

    cr = cr.copy()
    cr["地域偏在指数"] = cr.apply(rci_for, axis=1)
    cr_show = cr[["rank_in_municipality", "candidate", "party", "votes_f", "地域偏在指数"]].rename(
        columns={"rank_in_municipality": "順位", "candidate": "候補者", "party": "政党", "votes_f": "個人票"}
    ).set_index("順位")
    st.dataframe(cr_show.style.format({"個人票": "{:,.0f}", "地域偏在指数": "{:.0f}"}), use_container_width=True)

    st.caption("この自治体で特に強い(地域偏在指数が高い)候補者トップ5")
    standout = cr.dropna(subset=["地域偏在指数"]).sort_values("地域偏在指数", ascending=False).head(5)
    for _, r in standout.iterrows():
        bcol1, bcol2 = st.columns([5, 1.4])
        with bcol1:
            st.write(f"{r['candidate']}({r['party']}) ― 個人票 {r['votes_f']:,.0f}票・偏在指数 {r['地域偏在指数']:.0f}")
        with bcol2:
            if st.button("候補者分析へ", key=f"sp_d_jump_{r['party']}_{r['candidate_number']}"):
                goto("B. 候補者分析", sp_sel_year=year, sp_sel_party=r["party"], sp_sel_cnum=r["candidate_number"])

    other_year = 2022 if year == 2025 else 2025
    vv_other = spd.load_valid_votes(other_year)
    other_row = vv_other[vv_other["geometry_key"] == gkey]
    if not other_row.empty:
        other_valid = float(other_row["valid_votes"].iloc[0])
        st.markdown('<div class="sp-section-title">2022/2025 比較(この自治体)</div>', unsafe_allow_html=True)
        st.write(f"{other_year}年の比例有効票: {other_valid:,.0f}票(2025年との単純比較。境界変更があった地域は目安値です)")
    else:
        st.caption("もう一方の年はこの地物(geometry_key)に対応する選挙結果がありません(境界再編の可能性があります)。")

# ===========================================================================
# TAB E: 2022→2025比較
# ===========================================================================
elif active_tab == "E. 2022→2025比較":
    mode = st.radio("比較単位", ["政党で比較", "候補者で比較"], horizontal=True, key="sp_e_mode")

    if mode == "政党で比較":
        parties_both = sorted(set(spd.active_parties(2025)) & set(spd.active_parties(2022)))
        party_e = st.selectbox("政党(同一名称のみ。名称変更・後継関係の自動推定は行いません)", parties_both, key="sp_e_party")

        p25 = spd.party_municipality_table(2025, party_e)
        p22 = spd.party_municipality_table(2022, party_e)
        merged = p25[["geometry_key", "pref_name", "display_name", "region", "party_total_f", "party_share"]].merge(
            p22[["geometry_key", "party_total_f", "party_share"]], on="geometry_key", how="outer", suffixes=("_2025", "_2022")
        )
        merged["vote_diff"] = merged["party_total_f_2025"].fillna(0) - merged["party_total_f_2022"].fillna(0)
        merged["share_diff_pp"] = (merged["party_share_2025"].fillna(0) - merged["party_share_2022"].fillna(0)) * 100.0

        t25 = merged["party_total_f_2025"].fillna(0).sum()
        t22 = merged["party_total_f_2022"].fillna(0).sum()
        st.markdown(
            f"""
<div class="sp-stat-strip">
  <span><strong>{t25-t22:+,.0f}票</strong>全国得票数差</span>
  <span><strong>{(t25/spd.load_valid_votes(2025)['valid_votes'].apply(float).sum() - t22/spd.load_valid_votes(2022)['valid_votes'].apply(float).sum())*100:+.2f}pt</strong>全国得票率差</span>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sp-section-title">2025−2022 得票率差(pt)マップ</div>', unsafe_allow_html=True)
        merged_for_map = merged.dropna(subset=["display_name"]).copy()
        merged_for_map["hover"] = merged_for_map.apply(
            lambda r: f"<b>{r['pref_name']} {r['display_name']}</b><br>差 {r['share_diff_pp']:+.2f}pt", axis=1)
        web_geo25 = spd.load_web_geojson(2025)
        fig_map = spd.build_choropleth_figure(web_geo25, merged_for_map, "share_diff_pp", "hover", colorscale="RdBu",
                                               zmid=0, colorbar_title="pt差", height=620)
        st.plotly_chart(fig_map, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**増加TOP20(得票率pt差)**")
            up = merged.dropna(subset=["display_name"]).sort_values("share_diff_pp", ascending=False).head(20)
            st.dataframe(up[["pref_name", "display_name", "share_diff_pp"]].rename(
                columns={"pref_name": "都道府県", "display_name": "市区町村", "share_diff_pp": "差(pt)"}
            ).reset_index(drop=True).style.format({"差(pt)": "{:+.2f}"}), use_container_width=True, height=380)
        with c2:
            st.markdown("**減少TOP20(得票率pt差)**")
            down = merged.dropna(subset=["display_name"]).sort_values("share_diff_pp", ascending=True).head(20)
            st.dataframe(down[["pref_name", "display_name", "share_diff_pp"]].rename(
                columns={"pref_name": "都道府県", "display_name": "市区町村", "share_diff_pp": "差(pt)"}
            ).reset_index(drop=True).style.format({"差(pt)": "{:+.2f}"}), use_container_width=True, height=380)

        st.markdown('<div class="sp-section-title">地方別 構成変化</div>', unsafe_allow_html=True)
        region_comp = merged.dropna(subset=["display_name"]).groupby("region")[["party_total_f_2025", "party_total_f_2022"]].sum()
        region_comp = region_comp.reindex(spd.REGION_ORDER).fillna(0)
        fig_region = go.Figure()
        fig_region.add_trace(go.Bar(name="2022", x=region_comp.index, y=region_comp["party_total_f_2022"]))
        fig_region.add_trace(go.Bar(name="2025", x=region_comp.index, y=region_comp["party_total_f_2025"]))
        fig_region.update_layout(barmode="group", height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_region, use_container_width=True)

        export_df = merged.dropna(subset=["display_name"])[["pref_name", "display_name", "party_total_f_2022", "party_total_f_2025", "vote_diff", "share_diff_pp"]]
        st.download_button("この比較結果をCSVでダウンロード",
                            data=export_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"sangiin_pr_compare_party_{party_e}.csv", mime="text/csv")

    else:
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**2022年の候補者**")
            cands22 = spd.candidates_for(2022)
            labels22 = [f"{r['candidate']}({r['party']})" for _, r in cands22.iterrows()]
            lab22 = st.selectbox("候補者A", labels22, key="sp_e_cand22")
            row22 = cands22.iloc[labels22.index(lab22)]
        with cc2:
            st.markdown("**2025年の候補者**")
            cands25 = spd.candidates_for(2025)
            labels25 = [f"{r['candidate']}({r['party']})" for _, r in cands25.iterrows()]
            lab25 = st.selectbox("候補者B", labels25, key="sp_e_cand25")
            row25 = cands25.iloc[labels25.index(lab25)]

        df22 = spd.candidate_municipality_table(2022, row22["party"], row22["candidate_number"])
        df25 = spd.candidate_municipality_table(2025, row25["party"], row25["candidate_number"])
        stats22 = spd.concentration_stats(df22)
        stats25 = spd.concentration_stats(df25)

        merged = df25[["geometry_key", "pref_name", "display_name", "region", "candidate_valid_share"]].merge(
            df22[["geometry_key", "candidate_valid_share"]], on="geometry_key", how="outer", suffixes=("_B2025", "_A2022")
        )
        merged["share_diff_pp"] = (merged["candidate_valid_share_B2025"].fillna(0) - merged["candidate_valid_share_A2022"].fillna(0)) * 100.0

        st.markdown('<div class="sp-section-title">集票構造の比較</div>', unsafe_allow_html=True)
        colA, colB = st.columns(2)
        with colA:
            st.write(f"**A: {row22['candidate']}({row22['party']}, 2022)**")
            st.write(f"全国票: {float(row22['national_votes']):,.0f}票")
            st.write(f"N50={stats22['n50']} / N80={stats22['n80']} / HHI={fmt_num(stats22['hhi'],1)} / Gini={fmt_num(stats22['gini'],3)} / Entropy={fmt_num(stats22['entropy'],3)}")
        with colB:
            st.write(f"**B: {row25['candidate']}({row25['party']}, 2025)**")
            st.write(f"全国票: {float(row25['national_votes']):,.0f}票")
            st.write(f"N50={stats25['n50']} / N80={stats25['n80']} / HHI={fmt_num(stats25['hhi'],1)} / Gini={fmt_num(stats25['gini'],3)} / Entropy={fmt_num(stats25['entropy'],3)}")

        st.markdown('<div class="sp-section-title">個人票率 差分(pt)マップ(B2025−A2022)</div>', unsafe_allow_html=True)
        merged_for_map = merged.dropna(subset=["display_name"]).copy()
        merged_for_map["hover"] = merged_for_map.apply(
            lambda r: f"<b>{r['pref_name']} {r['display_name']}</b><br>差 {r['share_diff_pp']:+.3f}pt", axis=1)
        web_geo25 = spd.load_web_geojson(2025)
        fig_map = spd.build_choropleth_figure(web_geo25, merged_for_map, "share_diff_pp", "hover", colorscale="RdBu",
                                               zmid=0, colorbar_title="pt差", height=620)
        st.plotly_chart(fig_map, use_container_width=True)

        export_df = merged.dropna(subset=["display_name"])[["pref_name", "display_name", "candidate_valid_share_A2022", "candidate_valid_share_B2025", "share_diff_pp"]]
        st.download_button("この比較結果をCSVでダウンロード",
                            data=export_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="sangiin_pr_compare_candidates.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# フッター: データについて
# ---------------------------------------------------------------------------
with st.expander("データについて"):
    st.markdown(spd.data_quality_note())
    st.caption(
        "候補者番号は政党内のみで一意のため、候補者キーは(年, 政党, 候補者番号)の組で管理しています。"
        "按分票等の小数票は内部では丸めず、画面表示は小数第3位まで、CSVダウンロードは元の精度のまま出力しています。"
        "特定枠候補者(自民・れいわ等)は個人票の集計対象から除外し、候補者一覧には表示する場合「特定枠」バッジを付けています。"
    )
