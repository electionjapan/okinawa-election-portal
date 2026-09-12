from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd

GOOGLE_SHEET_ID = "1s6H3je6DPCSNIzwcOQpA39t_ecISuuAjY4qT2a291is"
SHEET_NAMES = [
    "00_候補者",
    "01_市町村マスター",
    "02_投票速報",
    "03_開票速報",
    "04_県集計",
    "06_無効票補正",
]

CURRENT_ATTR_BY_NAME = {
    "古謝 げんた": "保守系",
    "玉城 デニー": "オール沖縄系",
}


class LiveSheetError(RuntimeError):
    pass


def _csv_url(sheet_name: str, sheet_id: str = GOOGLE_SHEET_ID) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(sheet_name)}"
    )


def fetch_sheet_csv(sheet_name: str, sheet_id: str = GOOGLE_SHEET_ID, timeout: int = 12) -> pd.DataFrame:
    """Read one public Google Sheet tab through the GViz CSV endpoint."""
    url = _csv_url(sheet_name, sheet_id)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 OkinawaElectionPortal/0.9.22"})
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8-sig")
    except Exception as exc:  # network/auth failures are handled by caller
        raise LiveSheetError(f"{sheet_name} の取得に失敗しました: {exc}") from exc
    try:
        return pd.read_csv(StringIO(body), dtype=object, keep_default_na=True)
    except Exception as exc:
        raise LiveSheetError(f"{sheet_name} のCSV解析に失敗しました: {exc}") from exc


def load_google_workbook(sheet_id: str = GOOGLE_SHEET_ID) -> dict[str, pd.DataFrame]:
    book = {}
    for name in SHEET_NAMES:
        book[name] = fetch_sheet_csv(name, sheet_id=sheet_id)
    return book


def _num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return pd.NA
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip().replace(",", "").replace("票", "")
    if not s or s in {"-", "―", "—", "未発表", "未入力"}:
        return pd.NA
    if s.endswith("%"):
        s = s[:-1]
        try:
            return float(s) / 100.0
        except ValueError:
            return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def _rate(v):
    n = _num(v)
    if pd.isna(n):
        return pd.NA
    n = float(n)
    # Google CSV may return either 0.432 or 43.2 depending on cell formatting.
    if n > 1.0000001:
        n /= 100.0
    return max(0.0, min(1.0, n))


def _clean_text(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    return "" if s.lower() == "nan" else s


def _series_num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    return df[col].map(_num).astype("Float64")


def _series_rate(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    return df[col].map(_rate).astype("Float64")


def _normalize_candidate_name(name: str) -> str:
    return " ".join(str(name).replace("【入力】", "").split())


def _latest_update_text(values: pd.Series) -> str:
    raw = [_clean_text(v) for v in values.tolist()]
    raw = [v for v in raw if v]
    if not raw:
        return "未更新"
    parsed = []
    for s in raw:
        # Common forms: 22:30, 22:30:00, 2026/09/13 22:30
        for fmt in ("%H:%M", "%H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                parsed.append((dt, s))
                break
            except ValueError:
                pass
    if parsed:
        dt, s = max(parsed, key=lambda x: x[0])
        return dt.strftime("%H:%M") if dt.year == 1900 else dt.strftime("%m/%d %H:%M")
    return raw[-1]


def _safe_sum(series: pd.Series):
    s = pd.to_numeric(series, errors="coerce")
    return float(s.sum()) if s.notna().any() else pd.NA


def _normalize_correction_frame(df: pd.DataFrame) -> pd.DataFrame:
    if {"指標", "値"}.issubset(df.columns):
        return df.copy()
    # 06_無効票補正 has a title row before its real header. Depending on CSV parsing,
    # that title may have been consumed as the pandas header; find the row explicitly.
    for i in range(len(df)):
        row = [_clean_text(v) for v in df.iloc[i].tolist()]
        if row and row[0] == "指標" and len(row) >= 2 and row[1] == "値":
            out = df.iloc[i + 1 :, : min(3, df.shape[1])].copy()
            cols = ["指標", "値", "説明"][: out.shape[1]]
            out.columns = cols
            return out.reset_index(drop=True)
    return pd.DataFrame(columns=["指標", "値", "説明"])

@dataclass
class LiveModels:
    current: pd.DataFrame
    msum: pd.DataFrame
    totals: pd.DataFrame
    candidates: pd.DataFrame
    overall_reporting: float | None
    latest_update: str
    confirmed_count: int
    invalid_low: float | None
    invalid_center: float | None
    invalid_high: float | None
    correction_factor: float | None
    turnout_label: str


def build_live_models(book: dict[str, pd.DataFrame], municipalities: pd.DataFrame) -> LiveModels:
    cand = book["00_候補者"].copy()
    opening = book["03_開票速報"].copy()
    voting = book["02_投票速報"].copy()
    master = book["01_市町村マスター"].copy()
    correction = _normalize_correction_frame(book.get("06_無効票補正", pd.DataFrame()).copy())

    # Candidate metadata follows filing order from the sheet.
    cand = cand[cand.get("候補者名", pd.Series(dtype=object)).notna()].copy()
    cand["candidate_id"] = pd.to_numeric(cand.get("届出番号"), errors="coerce")
    cand["candidate_name"] = cand["候補者名"].map(_normalize_candidate_name)
    cand["party"] = cand.get("党派", "").map(_clean_text)
    cand["incumbency"] = cand.get("現新", "").map(_clean_text)
    cand["age"] = pd.to_numeric(cand.get("年齢"), errors="coerce")
    cand["title"] = cand.get("肩書", "").map(_clean_text)
    cand["endorsement"] = cand.get("推薦・支援", "").map(_clean_text)
    cand["attribute"] = cand["candidate_name"].map(CURRENT_ATTR_BY_NAME).fillna("独立・無所属")
    cand["result"] = ""
    cand = cand.sort_values("candidate_id", na_position="last").reset_index(drop=True)

    # Attach portal municipality codes by exact name. The sheet's numeric No. is not a JIS code.
    muni_ref = municipalities[["municipality_code", "municipality_name"]].copy()
    muni_ref["municipality_name"] = muni_ref["municipality_name"].astype(str).str.strip()
    opening["municipality_name"] = opening["市町村名"].astype(str).str.strip()
    opening = opening.merge(muni_ref, on="municipality_name", how="left")
    opening["municipality_code"] = opening["municipality_code"].map(lambda x: "" if pd.isna(x) else str(x))

    # Voting / electorate information.
    voting2 = voting.copy()
    voting2["municipality_name"] = voting2["市町村名"].astype(str).str.strip()
    voting2["turnout_rate"] = _series_rate(voting2, "投票率")
    voting2["voting_voters"] = _series_num(voting2, "投票者_計")
    voting2["electorate"] = _series_num(voting2, "当日有権者_計")
    voting2["voting_state"] = voting2.get("データ状態", "").map(_clean_text)
    voting2["voting_round"] = voting2.get("最新速報回", "").map(_clean_text)

    master2 = master.copy()
    master2["municipality_name"] = master2["市町村名"].astype(str).str.strip()
    master2["display_electorate"] = _series_num(master2, "表示有権者数")

    opening = opening.merge(
        voting2[["municipality_name", "turnout_rate", "voting_voters", "electorate", "voting_state", "voting_round"]],
        on="municipality_name", how="left"
    ).merge(
        master2[["municipality_name", "display_electorate"]],
        on="municipality_name", how="left"
    )

    opening["voters_total"] = _series_num(opening, "投票者数")
    opening["counted_ballots"] = _series_num(opening, "開票済票数")
    opening["candidate_votes_total"] = _series_num(opening, "候補者得票計")
    opening["invalid_final"] = _series_num(opening, "無効票_確定【入力】")
    opening["rejected"] = _series_num(opening, "不受理等【入力】")
    opening["remaining_votes"] = _series_num(opening, "残票")
    opening["reporting_rate"] = _series_rate(opening, "表示開票率")
    opening["invalid_low"] = _series_num(opening, "推計無効票_下限")
    opening["invalid_center"] = _series_num(opening, "推計無効票_中心")
    opening["invalid_high"] = _series_num(opening, "推計無効票_上限")
    opening["valid_remaining_low"] = _series_num(opening, "推計有効残票_少")
    opening["valid_remaining_high"] = _series_num(opening, "推計有効残票_多")
    opening["invalid_display"] = opening.get("推計無効票表示", "").map(_clean_text)
    opening["update_time"] = opening.get("更新時刻【入力】", "").map(_clean_text)

    # Prefer the final opening-sheet voter count; fallback to the final voting tab if present.
    opening["voters_total"] = opening["voters_total"].fillna(opening["voting_voters"])
    opening["electorate"] = opening["electorate"].fillna(opening["display_electorate"])

    # Fallback calculations only when sheet outputs are blank. Never replace a published 0 with missing.
    calc_counted = opening["candidate_votes_total"].fillna(0) + opening["invalid_final"].fillna(0) + opening["rejected"].fillna(0)
    opening["counted_ballots"] = opening["counted_ballots"].fillna(calc_counted)
    calc_remaining = (opening["voters_total"] - opening["counted_ballots"]).clip(lower=0)
    opening["remaining_votes"] = opening["remaining_votes"].fillna(calc_remaining)
    calc_reporting = (opening["counted_ballots"] / opening["voters_total"].replace(0, pd.NA)).clip(lower=0, upper=1)
    opening["reporting_rate"] = opening["reporting_rate"].fillna(calc_reporting)
    opening["reporting_available"] = opening["reporting_rate"].notna()
    opening["reporting_pct"] = 100 * opening["reporting_rate"].fillna(0)
    opening["reported_votes"] = opening["counted_ballots"].fillna(0)
    # Alias retained because existing sort/map helpers use this field name.
    opening["final_valid_votes"] = opening["voters_total"]

    # Candidate rows for existing map / comparison functions.
    current_rows = []
    for _, orow in opening.iterrows():
        for _, crow in cand.iterrows():
            cname = crow["candidate_name"]
            input_col = next(
                (col for col in opening.columns if _normalize_candidate_name(col) == cname and "【入力】" in str(col)),
                None,
            )
            val = _num(orow.get(input_col)) if input_col else pd.NA
            published = not pd.isna(val)
            current_rows.append({
                "municipality_code": str(orow.get("municipality_code", "")),
                "municipality_name": orow["municipality_name"],
                "candidate_id": int(crow["candidate_id"]) if pd.notna(crow["candidate_id"]) else 0,
                "candidate_name": cname,
                "party": crow["party"],
                "attribute": crow["attribute"],
                "result": "",
                "current_votes": 0 if not published else int(round(float(val))),
                "vote_published": published,
                "display_votes": pd.NA if not published else int(round(float(val))),
            })
    current = pd.DataFrame(current_rows)

    # Leader / margin per municipality.
    leaders = []
    for code, grp in current.groupby("municipality_code", dropna=False):
        grp = grp.sort_values(["current_votes", "candidate_id"], ascending=[False, True])
        total_candidate = int(grp["current_votes"].sum())
        top = grp.iloc[0] if len(grp) else None
        second = grp.iloc[1] if len(grp) > 1 else None
        top_votes = int(top["current_votes"]) if top is not None else 0
        second_votes = int(second["current_votes"]) if second is not None else 0
        tie = total_candidate > 0 and second is not None and top_votes == second_votes
        lead_votes = 0 if tie else (top_votes - second_votes if total_candidate else 0)
        lead_points = 100 * lead_votes / total_candidate if total_candidate else 0.0
        leaders.append({
            "municipality_code": str(code),
            "leader_name": "同数" if tie else (top["candidate_name"] if total_candidate and top is not None else "未開票"),
            "leader_attribute": "同数" if tie else (top["attribute"] if total_candidate and top is not None else ""),
            "lead_votes": lead_votes,
            "lead_points": lead_points,
            "is_tie": tie,
        })
    leader_df = pd.DataFrame(leaders)

    keep_cols = [
        "municipality_code", "municipality_name", "reported_votes", "counted_ballots",
        "candidate_votes_total", "voters_total", "electorate", "final_valid_votes",
        "reporting_pct", "reporting_available", "remaining_votes", "turnout_rate", "invalid_final", "rejected",
        "invalid_low", "invalid_center", "invalid_high", "valid_remaining_low", "valid_remaining_high",
        "invalid_display", "update_time", "voting_state", "voting_round",
    ]
    msum = opening[keep_cols].merge(leader_df, on="municipality_code", how="left")

    def _status(r):
        if pd.notna(r["reporting_pct"]) and float(r["reporting_pct"]) >= 99.95:
            return "確定"
        if pd.notna(r["remaining_votes"]) and float(r["remaining_votes"]) == 0 and pd.notna(r["voters_total"]) and float(r["voters_total"]) > 0:
            return "確定"
        if float(r.get("reported_votes") or 0) > 0 or (pd.notna(r["reporting_pct"]) and float(r["reporting_pct"]) > 0):
            return "開票中"
        return "未開票"
    msum["status"] = msum.apply(_status, axis=1)

    totals = current.groupby(
        ["candidate_id", "candidate_name", "party", "attribute", "result"], as_index=False
    ).agg(current_votes=("current_votes", "sum"), published_cells=("vote_published", "sum"))
    totals["has_published"] = totals["published_cells"] > 0
    totals = totals.merge(
        cand[["candidate_id", "incumbency", "age", "title", "endorsement"]], on="candidate_id", how="left"
    ).sort_values("candidate_id")
    denom = float(totals["current_votes"].sum())
    totals["pct"] = 100 * totals["current_votes"] / denom if denom > 0 else 0.0

    known = msum[msum["voters_total"].notna() & (msum["voters_total"] > 0)]
    if len(known) == len(msum) and len(msum) > 0 and float(known["voters_total"].sum()) > 0:
        overall_reporting = 100 * float(known["reported_votes"].sum()) / float(known["voters_total"].sum())
        overall_reporting = max(0.0, min(100.0, overall_reporting))
    else:
        overall_reporting = None

    confirmed_count = int((msum["status"] == "確定").sum())
    latest_update = _latest_update_text(opening["update_time"])

    # Province-wide invalid-vote range: confirmed actuals + unconfirmed estimates are already
    # assembled in 06_無効票補正. Fall back to summing 03 when necessary.
    invalid_low = invalid_center = invalid_high = correction_factor = None
    if not correction.empty and "指標" in correction.columns and "値" in correction.columns:
        cmap = {_clean_text(r["指標"]): r["値"] for _, r in correction.iterrows()}
        def cnum(key):
            v = _num(cmap.get(key))
            return None if pd.isna(v) else float(v)
        invalid_low = cnum("下限")
        invalid_center = cnum("中心")
        invalid_high = cnum("上限")
        correction_factor = cnum("適用補正係数")
    if invalid_low is None:
        invalid_low = _safe_sum(msum["invalid_low"])
        invalid_low = None if pd.isna(invalid_low) else invalid_low
    if invalid_center is None:
        invalid_center = _safe_sum(msum["invalid_center"])
        invalid_center = None if pd.isna(invalid_center) else invalid_center
    if invalid_high is None:
        invalid_high = _safe_sum(msum["invalid_high"])
        invalid_high = None if pd.isna(invalid_high) else invalid_high

    if not (len(known) == len(msum) and len(msum) > 0):
        invalid_low = invalid_center = invalid_high = None

    rounds = [x for x in voting2["voting_round"].tolist() if _clean_text(x) and _clean_text(x) != "未入力"]
    turnout_label = _clean_text(rounds[-1]) if rounds else "未入力"

    return LiveModels(
        current=current,
        msum=msum,
        totals=totals,
        candidates=cand,
        overall_reporting=overall_reporting,
        latest_update=latest_update,
        confirmed_count=confirmed_count,
        invalid_low=invalid_low,
        invalid_center=invalid_center,
        invalid_high=invalid_high,
        correction_factor=correction_factor,
        turnout_label=turnout_label,
    )
