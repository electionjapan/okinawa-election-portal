"""
参院比例 個人票分析ページ用データの検算スクリプト(指示書 13章)。

build_sangiin_pr_data.py とは独立に、
  (a) 元データ(--source 以下の生CSV)に含まれる検証用ファイル自体の内容
  (b) 前処理済みデータ(--processed、既定は data/sangiin_pr/processed)
の両方を検算する。build側のロジックを信用せず、ここでも生データから
再集計して突き合わせる。1件でも不一致があれば非ゼロ終了する
(「失敗したら黙って表示を続行せず、開発時に明確なエラーにする」)。

使い方:
    python3 scripts/validate_sangiin_pr_data.py --source /path/to/extracted
    python3 scripts/validate_sangiin_pr_data.py --source /path/to/extracted --processed data/sangiin_pr/processed
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PORTAL_DIR = SCRIPT_DIR.parent
DEFAULT_PROCESSED = PORTAL_DIR / "data" / "sangiin_pr" / "processed"

EXPECTED_2025_NATIONAL_TOTAL = Decimal("59185398.465")

# 指示書README記載の特定枠候補者一覧(突き合わせ用)
EXPECTED_SPECIAL_2025 = {
    ("自由民主党", "1"),
    ("自由民主党", "2"),
    ("れいわ新選組", "1"),
}
EXPECTED_SPECIAL_2022 = {
    ("自由民主党", "32"),
    ("自由民主党", "33"),
    ("れいわ新選組", "9"),
    ("ごぼうの党", "4"),
    ("ごぼうの党", "5"),
    ("ごぼうの党", "6"),
    ("ごぼうの党", "7"),
    ("ごぼうの党", "8"),
    ("ごぼうの党", "9"),
    ("ごぼうの党", "10"),
    ("ごぼうの党", "11"),
}

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"[NG] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def to_decimal(s: str) -> Decimal:
    s = (s or "").strip()
    return Decimal(s) if s else Decimal("0")


# ---------------------------------------------------------------------------
# セクション13-1: 2025年の検証用ファイル自体のチェック
# ---------------------------------------------------------------------------
def check_2025_source_validation_files(candidate_complete: Path) -> None:
    path = candidate_complete / "2025_national_validation_complete.csv"
    total_rows = 0
    ng_rows = 0
    national_total_row = None
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            status = row.get("status", "")
            if status != "OK":
                ng_rows += 1
            # 全国総得票の行を探す(列名はファイルの実際の構造に依存するため緩く探索)
            for k, v in row.items():
                if k and "national_total" in k.lower():
                    national_total_row = row
    if ng_rows:
        fail(f"2025_national_validation_complete.csv: status!=OK の行が {ng_rows}/{total_rows} 件あります")
    else:
        ok(f"2025_national_validation_complete.csv: 全{total_rows}行 status==OK")

    path2 = candidate_complete / "2025_remaining_candidate_person_detail_issues.csv"
    with open(path2, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if rows:
        fail(f"2025_remaining_candidate_person_detail_issues.csv に {len(rows)} 件の未解決issueがあります")
    else:
        ok("2025_remaining_candidate_person_detail_issues.csv: 0件(未解決issueなし)")

    path3 = candidate_complete / "2025_district_party_validation.csv"
    ng = []
    total = 0
    with open(path3, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total += 1
            # NG判定列を緩く探索(status/result/validation等にNGの文字列が含まれるか)
            is_ng = False
            for k, v in row.items():
                if v and str(v).strip().upper() == "NG":
                    is_ng = True
            if is_ng:
                ng.append(row)
    if ng:
        fail(f"2025_district_party_validation.csv: {len(ng)}/{total} 件がNGです")
    else:
        ok(f"2025_district_party_validation.csv: 全{total}行NGなし")

    # README記載の national_total も突き合わせ(README_COMPLETE_2025.txt は別ファイルなので
    # こちらは candidate_national_totals の合計で独立検算する(check_against_reference_totals 内))


def check_readme_complete_2025(candidate_complete: Path) -> None:
    path = candidate_complete / "README_COMPLETE_2025.txt"
    if not path.exists():
        warnings.append("README_COMPLETE_2025.txt が見つかりません(スキップ)")
        return
    text = path.read_text(encoding="utf-8")
    if '"unresolved_blocks_after": 0' not in text:
        fail("README_COMPLETE_2025.txt: unresolved_blocks_after が 0 ではありません")
    else:
        ok("README_COMPLETE_2025.txt: unresolved_blocks_after == 0")
    if '"national_total": "59185398.465"' not in text:
        fail("README_COMPLETE_2025.txt: national_total が 59185398.465 ではありません")
    else:
        ok("README_COMPLETE_2025.txt: national_total == 59185398.465")
    if '"district_party_validation_ng": 0' not in text:
        fail("README_COMPLETE_2025.txt: district_party_validation_ng が 0 ではありません")
    else:
        ok("README_COMPLETE_2025.txt: district_party_validation_ng == 0")


# ---------------------------------------------------------------------------
# セクション13-2: 生データからの独立再集計(year×district×party単位)
# ---------------------------------------------------------------------------
def independent_recount(votes_path: Path, totals_path: Path, year: int) -> dict:
    """district(=選挙結果側の生の district文字列、地図結合前)単位で検算する。
    地図結合(crosswalk)に依存せず、生データの district 名そのものをキーにすることで、
    build側のクロスウォークのバグがここでも検出できないようにならないよう、
    あえてbuildとは別のキー(district文字列)で独立に集計する。
    """
    cand_sum = defaultdict(lambda: Decimal("0"))
    party_name_sum = defaultdict(lambda: Decimal("0"))
    special_seen = set()
    all_special_rows_use_for_sum0 = True

    with open(votes_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("candidate_is_special") == "1":
                special_seen.add((row["party"], row["candidate_number"]))
                if row.get("use_for_sum") == "1":
                    all_special_rows_use_for_sum0 = False
            if row.get("row_scope") != "district" or row.get("use_for_sum") != "1":
                continue
            key = (row["prefecture_code"], row["district"], row["party"])
            v = to_decimal(row["votes"])
            if row["vote_type"] == "candidate":
                cand_sum[key] += v
            elif row["vote_type"] == "party_name":
                party_name_sum[key] += v

    party_total = defaultdict(lambda: Decimal("0"))
    candidate_sum_official = defaultdict(lambda: Decimal("0"))
    with open(totals_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("row_scope") != "district" or row.get("use_for_sum") != "1":
                continue
            key = (row["prefecture_code"], row["district"], row["party"])
            v = to_decimal(row["votes"])
            if row["vote_type"] == "party_total":
                party_total[key] += v
            elif row["vote_type"] == "candidate_sum":
                candidate_sum_official[key] += v

    if not all_special_rows_use_for_sum0:
        fail(f"{year}年: candidate_is_special==1 の行に use_for_sum==1 のものが含まれています(特定枠が個人票集計に混入する恐れ)")
    else:
        ok(f"{year}年: 特定枠候補者({len(special_seen)}名)は全件 use_for_sum==0 を確認")

    mism_cs = []
    for key in set(cand_sum) | set(candidate_sum_official):
        a, b = cand_sum.get(key, Decimal("0")), candidate_sum_official.get(key, Decimal("0"))
        if abs(a - b) > Decimal("0.001"):
            mism_cs.append((key, a, b))
    if mism_cs:
        fail(f"{year}年: Σ候補者個人票 != candidate_sum が {len(mism_cs)} 件 (例: {mism_cs[:3]})")
    else:
        ok(f"{year}年: 全district×partyで Σ候補者個人票 == candidate_sum")

    mism_pt = []
    for key in set(party_total) | set(candidate_sum_official) | set(party_name_sum):
        pn = party_name_sum.get(key, Decimal("0"))
        cs = candidate_sum_official.get(key, Decimal("0"))
        pt = party_total.get(key, Decimal("0"))
        if abs((pn + cs) - pt) > Decimal("0.001"):
            mism_pt.append((key, pn, cs, pt))
    if mism_pt:
        fail(f"{year}年: party_name+candidate_sum != party_total が {len(mism_pt)} 件 (例: {mism_pt[:3]})")
    else:
        ok(f"{year}年: 全district×partyで party_name+candidate_sum == party_total")

    valid_votes_by_district = defaultdict(lambda: Decimal("0"))
    for (pref_code, district, _party), v in party_total.items():
        valid_votes_by_district[(pref_code, district)] += v

    return {
        "cand_sum": cand_sum,
        "party_total": party_total,
        "valid_votes_by_district": valid_votes_by_district,
        "special_seen": special_seen,
    }


def check_special_candidate_lists(special_seen: set, expected: set, year: int) -> None:
    if special_seen != expected:
        missing = expected - special_seen
        extra = special_seen - expected
        fail(f"{year}年: 特定枠候補者リストがREADME記載と一致しません(不足={missing}, 余分={extra})")
    else:
        ok(f"{year}年: 特定枠候補者リストがREADME記載({len(expected)}名)と完全一致")


# ---------------------------------------------------------------------------
# セクション13-3: 2025 候補者別全国票 参照ファイルとの突き合わせ
# ---------------------------------------------------------------------------
def check_against_reference_totals(candidate_complete: Path, rec2025: dict) -> None:
    path = candidate_complete / "2025_candidate_national_totals.csv"
    if not path.exists():
        warnings.append("2025_candidate_national_totals.csv が見つかりません(突き合わせスキップ)")
        return

    # 独立再集計(district×party単位)から候補者別全国票を作る
    # ※ cand_sum のキーは (pref_code, district, party) 単位の「党全体」の個人票合計であり
    #   候補者別ではないため、ここでは生データを候補者番号単位で別途再集計する。
    cand_national = defaultdict(lambda: Decimal("0"))
    votes_path = candidate_complete / "2025_votes_long_complete.csv"
    with open(votes_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("row_scope") != "district" or row.get("use_for_sum") != "1":
                continue
            if row["vote_type"] != "candidate":
                continue
            key = (row["party"], row["candidate_number"])
            cand_national[key] += to_decimal(row["votes"])

    mism = []
    n_checked = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # 列名はファイルの実際の見出しに合わせて緩く探索する
        fieldnames = reader.fieldnames or []
        party_col = next((c for c in fieldnames if "party" in c.lower() or "政党" in c), None)
        num_col = next((c for c in fieldnames if "number" in c.lower() or "番号" in c), None)
        votes_col = next((c for c in fieldnames if "vote" in c.lower() or "票" in c), None)
        if not (party_col and num_col and votes_col):
            warnings.append(f"2025_candidate_national_totals.csv の列名を特定できませんでした(fieldnames={fieldnames})。突き合わせスキップ")
            return
        for row in reader:
            key = (row[party_col], row[num_col])
            ref_v = to_decimal(row[votes_col])
            got_v = cand_national.get(key, Decimal("0"))
            n_checked += 1
            if abs(ref_v - got_v) > Decimal("0.001"):
                mism.append((key, ref_v, got_v))

    if mism:
        fail(f"2025_candidate_national_totals.csv との不一致が {len(mism)}/{n_checked} 件 (例: {mism[:5]})")
    else:
        ok(f"2025_candidate_national_totals.csv: 全{n_checked}候補者で独立再集計と完全一致")


# ---------------------------------------------------------------------------
# セクション13-4: 前処理済みデータ(processed)の検算
# ---------------------------------------------------------------------------
def check_processed(processed: Path, year: int) -> None:
    cv_path = processed / f"candidate_votes_{year}.csv"
    pt_path = processed / f"party_totals_{year}.csv"
    mv_path = processed / f"municipality_valid_votes_{year}.csv"
    for p in (cv_path, pt_path, mv_path):
        if not p.exists():
            fail(f"{year}年: 前処理済みファイルが見つかりません: {p}")
            return

    cand_sum_by_gkey_party = defaultdict(lambda: Decimal("0"))
    with open(cv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            v = Decimal(row["votes"])
            # float変換で桁が壊れていないか(文字列としてDecimal可能か)を確認
            if "." in row["votes"]:
                frac = row["votes"].split(".")[1]
                if len(frac) > 3:
                    fail(f"{year}年: candidate_votes_{year}.csv に小数点以下4桁以上の値があります: {row['votes']}")
            cand_sum_by_gkey_party[(row["geometry_key"], row["party"])] += v

    party_total = {}
    candidate_sum_official = {}
    party_name_votes = {}
    with open(pt_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["geometry_key"], row["party"])
            party_total[key] = Decimal(row["party_total"])
            candidate_sum_official[key] = Decimal(row["candidate_sum"])
            party_name_votes[key] = Decimal(row["party_name_votes"])

    mism_cs = 0
    for key, v in cand_sum_by_gkey_party.items():
        if abs(v - candidate_sum_official.get(key, Decimal("0"))) > Decimal("0.001"):
            mism_cs += 1
    if mism_cs:
        fail(f"{year}年(processed): Σcandidate_votes != candidate_sum が {mism_cs} 件")
    else:
        ok(f"{year}年(processed): candidate_votes_{year}.csv の合計が party_totals_{year}.csv の candidate_sum と一致")

    mism_pt = 0
    for key in set(party_total) | set(candidate_sum_official) | set(party_name_votes):
        pn = party_name_votes.get(key, Decimal("0"))
        cs = candidate_sum_official.get(key, Decimal("0"))
        pt = party_total.get(key, Decimal("0"))
        if abs((pn + cs) - pt) > Decimal("0.001"):
            mism_pt += 1
    if mism_pt:
        fail(f"{year}年(processed): party_name_votes+candidate_sum != party_total が {mism_pt} 件")
    else:
        ok(f"{year}年(processed): party_totals_{year}.csv 内で party_name+candidate_sum == party_total")

    valid_votes = {}
    with open(mv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            valid_votes[row["geometry_key"]] = Decimal(row["valid_votes"])

    sum_pt_by_gkey = defaultdict(lambda: Decimal("0"))
    for (gkey, _party), v in party_total.items():
        sum_pt_by_gkey[gkey] += v

    mism_vv = 0
    for gkey in set(sum_pt_by_gkey) | set(valid_votes):
        a, b = sum_pt_by_gkey.get(gkey, Decimal("0")), valid_votes.get(gkey, Decimal("0"))
        if abs(a - b) > Decimal("0.001"):
            mism_vv += 1
    if mism_vv:
        fail(f"{year}年(processed): Σparty_total != valid_votes が {mism_vv} 市区町村で不一致")
    else:
        ok(f"{year}年(processed): 全市区町村で Σparty_total == valid_votes")

    if year == 2025:
        total = sum(valid_votes.values())
        if abs(total - EXPECTED_2025_NATIONAL_TOTAL) > Decimal("0.001"):
            fail(f"2025年(processed): 全国総得票が {total} で、期待値 {EXPECTED_2025_NATIONAL_TOTAL} と一致しません")
        else:
            ok(f"2025年(processed): 全国総得票 == {EXPECTED_2025_NATIONAL_TOTAL} と完全一致")


def check_map_join(processed: Path, year: int) -> None:
    cw_path = processed / f"crosswalk_{year}.csv"
    mv_path = processed / f"municipality_valid_votes_{year}.csv"
    if not cw_path.exists() or not mv_path.exists():
        fail(f"{year}年: crosswalk/municipality_valid_votesファイルが見つかりません")
        return

    districts_in_crosswalk = set()
    gkeys_from_crosswalk = set()
    with open(cw_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            districts_in_crosswalk.add((row["prefecture_code"], row["district"]))
            gkeys_from_crosswalk.add(row["geometry_key"])

    gkeys_in_valid_votes = set()
    with open(mv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            gkeys_in_valid_votes.add(row["geometry_key"])

    unjoined_valid_votes = gkeys_in_valid_votes - gkeys_from_crosswalk
    if unjoined_valid_votes:
        fail(f"{year}年: valid_votesにあるが地図結合先が無いgeometry_keyが{len(unjoined_valid_votes)}件: {list(unjoined_valid_votes)[:10]}")
    else:
        ok(f"{year}年: valid_votesの全geometry_keyが地図結合済み(0件未結合)")

    # geometry_keyの重複チェック(薩摩川内市の2025第1/第2のみ許容)
    from collections import Counter
    rev = Counter()
    with open(cw_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rev[row["geometry_key"]] += 1
    unexpected_dupes = {k: v for k, v in rev.items() if v > 1 and k != "46215"}
    if unexpected_dupes:
        fail(f"{year}年: 想定外のgeometry_key重複: {unexpected_dupes}")
    else:
        ok(f"{year}年: geometry_key重複は薩摩川内市(46215)のみ(想定通り)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="展開済み元データのルートディレクトリ")
    ap.add_argument("--processed", default=str(DEFAULT_PROCESSED), help="前処理済みデータのディレクトリ")
    args = ap.parse_args()

    source = Path(args.source)
    processed = Path(args.processed)
    candidate_complete = source / "candidate_complete"
    proportional = source / "proportional" / "election_data"

    print("=" * 70)
    print("1. 2025年 元データ付属の検証ファイル自体のチェック")
    print("=" * 70)
    check_2025_source_validation_files(candidate_complete)
    check_readme_complete_2025(candidate_complete)

    print()
    print("=" * 70)
    print("2. 生データからの独立再集計(district×party単位、クロスウォーク非依存)")
    print("=" * 70)
    rec2025 = independent_recount(
        candidate_complete / "2025_votes_long_complete.csv",
        candidate_complete / "2025_totals_long_complete.csv",
        2025,
    )
    check_special_candidate_lists(rec2025["special_seen"], EXPECTED_SPECIAL_2025, 2025)

    rec2022 = independent_recount(
        proportional / "2022_votes_long.csv",
        proportional / "2022_totals_long.csv",
        2022,
    )
    check_special_candidate_lists(rec2022["special_seen"], EXPECTED_SPECIAL_2022, 2022)

    total_2025_independent = sum(rec2025["valid_votes_by_district"].values())
    if abs(total_2025_independent - EXPECTED_2025_NATIONAL_TOTAL) > Decimal("0.001"):
        fail(f"2025年: 生データからの独立再集計の全国総得票が {total_2025_independent} で期待値と不一致")
    else:
        ok(f"2025年: 生データからの独立再集計でも全国総得票 == {EXPECTED_2025_NATIONAL_TOTAL}")

    print()
    print("=" * 70)
    print("3. 2025_candidate_national_totals.csv との突き合わせ")
    print("=" * 70)
    check_against_reference_totals(candidate_complete, rec2025)

    print()
    print("=" * 70)
    print("4. 前処理済みデータ(processed)の検算")
    print("=" * 70)
    check_processed(processed, 2025)
    check_processed(processed, 2022)

    print()
    print("=" * 70)
    print("5. 地図結合の検証")
    print("=" * 70)
    check_map_join(processed, 2025)
    check_map_join(processed, 2022)

    print()
    print("=" * 70)
    if warnings:
        print(f"警告 {len(warnings)}件:")
        for w in warnings:
            print(f"  [WARN] {w}")
    if errors:
        print(f"検算NG: {len(errors)}件のエラーがあります。")
        for e in errors:
            print(f"  - {e}")
        print("=" * 70)
        return 1
    print("検算OK: すべてのチェックに合格しました。")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
