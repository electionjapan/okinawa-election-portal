"""
参院比例 個人票分析ページ(sangiin_pr.py)用のデータ読み込み・指標計算モジュール。

- scripts/build_sangiin_pr_data.py が生成した data/sangiin_pr/processed/*.csv と
  data/sangiin_pr/geo/* だけを読み込む(70MB級の生CSVや44MB級detail GeoJSON単体は
  直接読み込まない)。
- 指標の定義(候補者個人票率・党内候補者占有率・全国票寄与率・地域偏在指数・
  N50/N80・HHI/Gini/正規化エントロピー)は指示書6章の数式のまま実装し、Claude側で
  勝手に変更しない。
- @st.cache_data / @st.cache_resource でキャッシュし、フィルタ変更ごとに全件再読込・
  全候補者×全自治体のクロス積を作らない(指示書12章)。
"""
from __future__ import annotations

import csv
import json
import math
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data" / "sangiin_pr"
PROCESSED_DIR = DATA_DIR / "processed"
GEO_DIR = DATA_DIR / "geo"

YEARS = [2025, 2022]

# ---------------------------------------------------------------------------
# 都道府県 -> 地方(固定マスタ。指示書7章の例示に沿った区分。将来的に差し替え可能)
# ---------------------------------------------------------------------------
PREF_REGION = {
    "01": "北海道",
    "02": "東北", "03": "東北", "04": "東北", "05": "東北", "06": "東北", "07": "東北",
    "08": "関東", "09": "関東", "10": "関東", "11": "関東", "12": "関東", "13": "関東", "14": "関東", "19": "関東",
    "15": "北陸信越", "16": "北陸信越", "17": "北陸信越", "18": "北陸信越", "20": "北陸信越",
    "21": "東海", "22": "東海", "23": "東海", "24": "東海",
    "25": "近畿", "26": "近畿", "27": "近畿", "28": "近畿", "29": "近畿", "30": "近畿",
    "31": "中国", "32": "中国", "33": "中国", "34": "中国", "35": "中国",
    "36": "四国", "37": "四国", "38": "四国", "39": "四国",
    "40": "九州・沖縄", "41": "九州・沖縄", "42": "九州・沖縄", "43": "九州・沖縄",
    "44": "九州・沖縄", "45": "九州・沖縄", "46": "九州・沖縄", "47": "九州・沖縄",
}
REGION_ORDER = ["北海道", "東北", "関東", "北陸信越", "東海", "近畿", "中国", "四国", "九州・沖縄"]

# ---------------------------------------------------------------------------
# 固定の政党カラー(主要政党は通念的な色、未定義分はハッシュから固定生成し、
# 再実行してもリロードごとに色が変わらないようにする)
# ---------------------------------------------------------------------------
_PARTY_COLORS_FIXED = {
    "自由民主党": "#D7000F",
    "立憲民主党": "#00428E",
    "日本維新の会": "#6FBA2C",
    "公明党": "#F39800",
    "国民民主党": "#004098",
    "日本共産党": "#A3001E",
    "れいわ新選組": "#E4007F",
    "社会民主党": "#00A95F",
    "参政党": "#FF6600",
    "チームみらい": "#00B5AD",
    "ＮＨＫ党": "#808080",
    "ごぼうの党": "#8B5A2B",
}
_FALLBACK_PALETTE = [
    "#5B5B8C", "#B3832C", "#3D7068", "#9C4F96", "#6A6A6A",
    "#C06C3B", "#2E7D96", "#8C3F3F", "#5A8F4C", "#7A5C9E",
]


def party_color(party: str) -> str:
    if party in _PARTY_COLORS_FIXED:
        return _PARTY_COLORS_FIXED[party]
    idx = sum(ord(c) for c in party) % len(_FALLBACK_PALETTE)
    return _FALLBACK_PALETTE[idx]


def admin_type(display_name: str, pref_code: str) -> str:
    """display_name(市区町村名)から行政区分を分類する(初期フェーズ: 人口非依存)。"""
    if display_name.endswith("区"):
        return "東京23区" if pref_code == "13" else "指定都市の区"
    if display_name.endswith("市"):
        return "市"
    if display_name.endswith("町"):
        return "町"
    if display_name.endswith("村"):
        return "村"
    return "その他"


# ---------------------------------------------------------------------------
# 基礎データ読み込み(キャッシュ)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_candidate_votes(year: int) -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / f"candidate_votes_{year}.csv",
        dtype={"geometry_key": str, "candidate_number": str, "candidate_is_special": int},
    )
    df["votes"] = df["votes"].astype(str).map(Decimal)
    return df


@st.cache_data(show_spinner=False)
def load_party_totals(year: int) -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / f"party_totals_{year}.csv", dtype={"geometry_key": str})
    for col in ("party_total", "candidate_sum", "party_name_votes"):
        df[col] = df[col].astype(str).map(Decimal)
    return df


@st.cache_data(show_spinner=False)
def load_valid_votes(year: int) -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / f"municipality_valid_votes_{year}.csv", dtype={"geometry_key": str})
    df["valid_votes"] = df["valid_votes"].astype(str).map(Decimal)
    return df


@st.cache_data(show_spinner=False)
def load_geo_master(year: int) -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / f"municipality_geo_master_{year}.csv",
        dtype={"geometry_key": str, "pref_code": str, "has_election_data": int},
    )
    df["region"] = df["pref_code"].map(PREF_REGION)
    df["admin_type"] = [admin_type(dn, pc) for dn, pc in zip(df["display_name"], df["pref_code"])]
    return df


@st.cache_data(show_spinner=False)
def load_candidate_master() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "candidate_master.csv", dtype={"candidate_number": str, "candidate_is_special": int})
    df["national_votes"] = df["national_votes"].astype(str).map(Decimal)
    return df


@st.cache_data(show_spinner=False)
def load_special_candidates(year: int) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"special_candidates_{year}.csv", dtype={"candidate_number": str})


@st.cache_resource(show_spinner=False)
def load_web_geojson(year: int) -> dict:
    with open(GEO_DIR / f"japan_{year}_web.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def load_prefectures_geojson() -> dict:
    with open(GEO_DIR / "prefectures.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def load_detail_geojson(year: int, pref_code: str) -> dict | None:
    path = GEO_DIR / "detail" / str(year) / f"{pref_code}.geojson"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def active_parties(year: int) -> list[str]:
    pt = load_party_totals(year)
    return sorted(pt["party"].unique().tolist())


def candidates_for(year: int, party: str | None = None) -> pd.DataFrame:
    cm = load_candidate_master()
    df = cm[(cm["year"] == year) & (cm["candidate_is_special"] == 0)]
    if party:
        df = df[df["party"] == party]
    return df.sort_values("national_votes", ascending=False)


def search_candidates(year: int, query: str) -> pd.DataFrame:
    """候補者名の部分一致検索(全角/半角スペース除去程度の軽い正規化)。"""
    cm = load_candidate_master()
    df = cm[(cm["year"] == year) & (cm["candidate_is_special"] == 0)]
    if not query:
        return df.sort_values("national_votes", ascending=False)
    q = query.strip().replace(" ", "").replace("　", "")
    mask = df["candidate"].astype(str).str.replace(" ", "").str.replace("　", "").str.contains(q, na=False)
    return df[mask].sort_values("national_votes", ascending=False)


def special_candidates_for_party(year: int, party: str) -> pd.DataFrame:
    sc = load_special_candidates(year)
    return sc[sc["party"] == party]


# ---------------------------------------------------------------------------
# 候補者単位の全自治体テーブル(0埋めは候補者選択時のみ生成。常設テーブル化しない)
# ---------------------------------------------------------------------------
def candidate_municipality_table(year: int, party: str, candidate_number: str) -> pd.DataFrame:
    """指示書6章の数式に基づく、選択した候補者の自治体別指標テーブルを返す。

    valid_votes_m            = Σ party_total(m, 全政党)                      … municipality_valid_votes
    candidate_valid_share    = candidate_votes(c,m) / valid_votes_m
    candidate_within_party_share = candidate_votes(c,m) / candidate_sum(p,m)  (candidate_sum==0 は NA)
    national_contribution    = candidate_votes(c,m) / candidate_national_votes(c)
    regional_concentration_index = (local_share / national_share) * 100
        local_share    = candidate_votes(c,m) / candidate_sum(p,m)
        national_share = candidate_national_votes(c) / party_candidate_votes_national(p)
    """
    geo = load_geo_master(year)
    geo = geo[geo["has_election_data"] == 1][["geometry_key", "pref_code", "pref_name", "display_name", "region", "admin_type"]].copy()

    cv = load_candidate_votes(year)
    cv_c = cv[(cv["party"] == party) & (cv["candidate_number"] == candidate_number)][["geometry_key", "votes"]]
    cv_c = cv_c.rename(columns={"votes": "candidate_votes"})

    pt = load_party_totals(year)
    pt_p = pt[pt["party"] == party][["geometry_key", "candidate_sum"]].rename(columns={"candidate_sum": "party_candidate_sum"})

    vv = load_valid_votes(year)[["geometry_key", "valid_votes"]]

    df = geo.merge(cv_c, on="geometry_key", how="left").merge(pt_p, on="geometry_key", how="left").merge(vv, on="geometry_key", how="left")
    df["candidate_votes"] = df["candidate_votes"].apply(lambda v: v if isinstance(v, Decimal) else Decimal("0"))
    df["party_candidate_sum"] = df["party_candidate_sum"].apply(lambda v: v if isinstance(v, Decimal) else Decimal("0"))
    df["valid_votes"] = df["valid_votes"].apply(lambda v: v if isinstance(v, Decimal) else Decimal("0"))

    cm = load_candidate_master()
    row = cm[(cm["year"] == year) & (cm["party"] == party) & (cm["candidate_number"] == candidate_number)]
    candidate_name = row["candidate"].iloc[0] if not row.empty else ""
    candidate_national_votes = row["national_votes"].iloc[0] if not row.empty else Decimal("0")
    party_candidate_votes_national = pt_p["party_candidate_sum"].sum()
    national_share = (
        (candidate_national_votes / party_candidate_votes_national) if party_candidate_votes_national > 0 else None
    )

    def f_share(row):
        return float(row["candidate_votes"]) / float(row["valid_votes"]) if row["valid_votes"] > 0 else None

    def f_within(row):
        return float(row["candidate_votes"]) / float(row["party_candidate_sum"]) if row["party_candidate_sum"] > 0 else None

    def f_contrib(row):
        return float(row["candidate_votes"]) / float(candidate_national_votes) if candidate_national_votes > 0 else None

    def f_rci(row):
        if row["party_candidate_sum"] <= 0 or national_share is None or national_share == 0:
            return None
        local_share = float(row["candidate_votes"]) / float(row["party_candidate_sum"])
        return (local_share / float(national_share)) * 100.0

    df["candidate_valid_share"] = df.apply(f_share, axis=1)
    df["candidate_within_party_share"] = df.apply(f_within, axis=1)
    df["national_contribution"] = df.apply(f_contrib, axis=1)
    df["regional_concentration_index"] = df.apply(f_rci, axis=1)
    df["candidate_votes_f"] = df["candidate_votes"].astype(float)
    df["valid_votes_f"] = df["valid_votes"].astype(float)
    df.attrs["candidate_name"] = candidate_name
    df.attrs["candidate_national_votes"] = float(candidate_national_votes)
    df.attrs["party_candidate_votes_national"] = float(party_candidate_votes_national)
    return df


def concentration_stats(df: pd.DataFrame) -> dict:
    """N50/N80/HHI/Gini/正規化エントロピー(指示書6章)。"""
    votes = df["candidate_votes_f"].to_numpy()
    total = votes.sum()
    n = len(votes)

    if total <= 0:
        return {"n50": None, "n80": None, "hhi": None, "gini": None, "entropy": None, "total": 0.0}

    sorted_desc = sorted(votes, reverse=True)
    cum = 0.0
    n50 = n80 = None
    for i, v in enumerate(sorted_desc, start=1):
        cum += v
        share = cum / total
        if n50 is None and share >= 0.5:
            n50 = i
        if n80 is None and share >= 0.8:
            n80 = i
            break

    shares = votes / total
    hhi = float((shares ** 2).sum() * 10000.0)

    # Gini: 全自治体(0票含む)を母集団とする。昇順に並べた v_1..v_n に対し
    # G = (2*Σ i*v_i)/(n*Σv_i) - (n+1)/n
    sv = sorted(votes)
    weighted_sum = sum((i + 1) * v for i, v in enumerate(sv))
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1) / n if n > 0 and total > 0 else None

    positive = votes[votes > 0]
    if len(positive) > 1:
        p = positive / positive.sum()
        h_raw = -sum(x * math.log(x) for x in p)
        entropy = h_raw / math.log(len(positive))
    elif len(positive) == 1:
        entropy = 0.0
    else:
        entropy = None

    return {"n50": n50, "n80": n80, "hhi": hhi, "gini": gini, "entropy": entropy, "total": total}


def cumulative_curve(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["candidate_votes_f"] > 0].sort_values("candidate_votes_f", ascending=False).reset_index(drop=True)
    total = sub["candidate_votes_f"].sum()
    if total <= 0:
        return pd.DataFrame({"n": [], "pct": []})
    sub["cum"] = sub["candidate_votes_f"].cumsum()
    sub["pct"] = 100.0 * sub["cum"] / total
    sub["n"] = range(1, len(sub) + 1)
    return sub[["n", "pct", "display_name", "pref_name", "candidate_votes_f"]]


# ---------------------------------------------------------------------------
# 政党単位の自治体テーブル(タブC: 政党分析)
# ---------------------------------------------------------------------------
def party_municipality_table(year: int, party: str) -> pd.DataFrame:
    geo = load_geo_master(year)
    geo = geo[geo["has_election_data"] == 1][["geometry_key", "pref_code", "pref_name", "display_name", "region", "admin_type"]].copy()
    pt = load_party_totals(year)
    pt_p = pt[pt["party"] == party][["geometry_key", "party_total", "candidate_sum", "party_name_votes"]]
    vv = load_valid_votes(year)[["geometry_key", "valid_votes"]]
    df = geo.merge(pt_p, on="geometry_key", how="left").merge(vv, on="geometry_key", how="left")
    for col in ("party_total", "candidate_sum", "party_name_votes"):
        df[col] = df[col].apply(lambda v: v if isinstance(v, Decimal) else Decimal("0"))
    df["valid_votes"] = df["valid_votes"].apply(lambda v: v if isinstance(v, Decimal) else Decimal("0"))

    df["party_total_f"] = df["party_total"].astype(float)
    df["valid_votes_f"] = df["valid_votes"].astype(float)
    df["party_share"] = df.apply(lambda r: float(r["party_total"]) / float(r["valid_votes"]) if r["valid_votes"] > 0 else None, axis=1)
    df["party_name_share"] = df.apply(lambda r: float(r["party_name_votes"]) / float(r["party_total"]) if r["party_total"] > 0 else None, axis=1)
    df["candidate_vote_share"] = df.apply(lambda r: float(r["candidate_sum"]) / float(r["party_total"]) if r["party_total"] > 0 else None, axis=1)
    return df


# ---------------------------------------------------------------------------
# 自治体単位テーブル(タブD: 自治体カルテ)
# ---------------------------------------------------------------------------
def municipality_party_ranking(year: int, geometry_key: str) -> pd.DataFrame:
    pt = load_party_totals(year)
    vv = load_valid_votes(year)
    valid = vv[vv["geometry_key"] == geometry_key]["valid_votes"]
    valid_votes = valid.iloc[0] if not valid.empty else Decimal("0")
    sub = pt[pt["geometry_key"] == geometry_key].copy()
    sub["share"] = sub["party_total"].apply(lambda v: float(v) / float(valid_votes) if valid_votes > 0 else None)
    sub["party_total_f"] = sub["party_total"].astype(float)
    sub["candidate_sum_f"] = sub["candidate_sum"].astype(float)
    sub["party_name_votes_f"] = sub["party_name_votes"].astype(float)
    return sub.sort_values("party_total_f", ascending=False)


def municipality_candidate_ranking(year: int, geometry_key: str) -> pd.DataFrame:
    cv = load_candidate_votes(year)
    sub = cv[cv["geometry_key"] == geometry_key].copy()
    sub["votes_f"] = sub["votes"].astype(float)
    sub = sub[sub["candidate_is_special"] == 0]
    sub = sub.sort_values("votes_f", ascending=False)
    sub["rank_in_municipality"] = range(1, len(sub) + 1)
    return sub


# ---------------------------------------------------------------------------
# 地図Figure構築(Plotly Choroplethmap。全国1900地物をベクタ化して1トレースで描画)
# ---------------------------------------------------------------------------
def build_choropleth_figure(geo_json: dict, df: pd.DataFrame, value_col: str, hover_col: str,
                             colorscale="YlOrRd", zmid=None, zmin=None, zmax=None,
                             colorbar_title: str = "", height: int = 640):
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Choroplethmap(
            geojson=geo_json,
            locations=df["geometry_key"],
            z=df[value_col],
            featureidkey="properties.geometry_key",
            colorscale=colorscale,
            zmid=zmid,
            zmin=zmin,
            zmax=zmax,
            marker_line_width=0.3,
            marker_line_color="#FFFFFF",
            text=df[hover_col],
            hovertemplate="%{text}<extra></extra>",
            colorbar=dict(title=colorbar_title, thickness=14),
        )
    )
    fig.update_layout(
        map=dict(style="open-street-map", zoom=4.1, center=dict(lat=36.5, lon=137.5)),
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
    )
    return fig


def hover_text_candidate(row) -> str:
    lines = [f"<b>{row['pref_name']} {row['display_name']}</b>"]
    lines.append(f"個人票: {row['candidate_votes_f']:,.0f}票")
    if pd.notna(row.get("candidate_valid_share")):
        lines.append(f"比例有効票比: {row['candidate_valid_share']*100:.2f}%")
    if pd.notna(row.get("candidate_within_party_share")):
        lines.append(f"党内占有率: {row['candidate_within_party_share']*100:.2f}%")
    if pd.notna(row.get("national_contribution")):
        lines.append(f"全国票寄与率: {row['national_contribution']*100:.3f}%")
    if pd.notna(row.get("regional_concentration_index")):
        lines.append(f"地域偏在指数: {row['regional_concentration_index']:.0f}")
    return "<br>".join(lines)


def data_quality_note() -> str:
    return (
        "2025年の候補者個人票は、総務省公表の基礎データをもとに、青森・岩手・和歌山・鳥取・佐賀・宮崎の"
        "6県選挙管理委員会の確定資料で欠落・不整合(60ブロック)を復元した完全版を使用しています。"
        "候補者個人票の未解決ブロックは0件です。"
        "地図は国土数値情報(N03)をもとに作成した行政区域境界を使用しています。全国の基準年は2014年4月1日"
        "時点の境界で、浜松市のみ2025年1月時点(中央区・浜名区・天竜区の新3区)の境界に置き換えています。"
        "富谷町など、地図の形状が旧名称に基づく市区町村についても、画面上の表示名は選挙が行われた当時の"
        "名称(選挙結果側の名称)を使用しています。"
    )
