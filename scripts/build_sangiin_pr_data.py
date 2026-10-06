"""
参院比例 個人票分析ページ用のデータ前処理スクリプト。

元データ(sangiin_2025_candidate_complete.zip / sangiin_2025_2022_proportional.zip /
geo_light.zip / japan_2022_detail.zip / japan_2025_detail.zip)を展開したディレクトリから、
ページが実行時に読み込む軽量な加工済みファイルを data/sangiin_pr/ 以下に生成する。

実行時(Streamlitアプリ側)はこのスクリプトの「出力」だけを読み、元の巨大CSV(70MB級)や
44MB級のdetail GeoJSONを直接読み込まない。detail GeoJSONは都道府県単位に分割して
data/sangiin_pr/geo/detail/{year}/{pref_code}.geojson として保存し、拡大表示時だけ
該当都道府県の小さいファイルを読む。

使い方:
    python3 scripts/build_sangiin_pr_data.py --source /path/to/extracted

--source 以下に次のディレクトリ構成を想定する(zipをそれぞれ展開したもの):
    <source>/candidate_complete/2025_votes_long_complete.csv
    <source>/candidate_complete/2025_totals_long_complete.csv
    <source>/candidate_complete/2025_candidate_national_totals.csv  (検算用)
    <source>/proportional/election_data/2022_votes_long.csv
    <source>/proportional/election_data/2022_totals_long.csv
    <source>/geo_light/geo/japan_2022_web.geojson
    <source>/geo_light/geo/japan_2025_web.geojson
    <source>/geo_light/geo/prefectures.geojson
    <source>/geo_light/geo/municipality_master_2022.csv
    <source>/geo_light/geo/municipality_master_2025.csv
    <source>/japan_2022_detail/japan_2022_detail.geojson
    <source>/japan_2025_detail/japan_2025_detail.geojson

本番配布物(GitHubアップロード用ZIP)には、70MB級の votes_long 系CSVや44MB級の
detail GeoJSON単体ファイルは含めない。ここで生成した data/sangiin_pr/processed/ と
data/sangiin_pr/geo/ (web版 + 都道府県別に分割したdetail + prefectures.geojson +
municipality_master) だけを配布物に含める。
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PORTAL_DIR = SCRIPT_DIR.parent
DATA_DIR = PORTAL_DIR / "data" / "sangiin_pr"
PROCESSED_DIR = DATA_DIR / "processed"
GEO_DIR = DATA_DIR / "geo"

# ---------------------------------------------------------------------------
# 指示書 3-1: 名称表記差・旧名称の明示的クロスウォーク
# ---------------------------------------------------------------------------
EXPLICIT_OVERRIDES = {
    ("青森県", "六ヶ所村"): "02411",
    ("青森県", "鯵ヶ沢町"): "02321",
    ("宮城県", "七ヶ宿町"): "04302",
    ("宮城県", "七ヶ浜町"): "04404",
    ("宮城県", "富谷市"): "04423",
    ("東京都", "青ヶ島村"): "13402",
    ("神奈川県", "茅ヶ崎市"): "14207",
    ("兵庫県", "丹波篠山市"): "28221",
    ("高知県", "梼原町"): "39405",
    ("福岡県", "那珂川市"): "40305",
    ("宮崎県", "五ヶ瀬町"): "45443",
}


def to_decimal(s: str) -> Decimal:
    s = (s or "").strip()
    return Decimal(s) if s else Decimal("0")


def load_master(geo_light: Path, year: int):
    path = geo_light / "geo" / f"municipality_master_{year}.csv"
    lookup, by_key = {}, {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            norm = (row["municipality_name"] + row["ward_name"]).replace(" ", "")
            lookup[(row["pref_code"], norm)] = (row["geometry_key"], row["display_name"])
            by_key[row["geometry_key"]] = row
    return lookup, by_key


def collect_districts(csv_path: Path):
    seen = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("row_scope") != "district" or row.get("use_for_sum") != "1":
                continue
            seen.add((row["prefecture_code"], row["prefecture"], row["district"]))
    return sorted(seen)


def build_crosswalk(geo_light: Path, year: int, district_rows):
    lookup, _by_key = load_master(geo_light, year)
    crosswalk, unmatched = {}, []
    for pref_code, pref_name, district in district_rows:
        norm = district.replace(" ", "")
        key = (pref_code, norm)
        gkey = None
        if key in lookup:
            gkey = lookup[key][0]
        elif district in ("薩摩川内市第１", "薩摩川内市第２", "薩摩川内市第1", "薩摩川内市第2"):
            gkey = "46215"
        elif pref_code == "04" and norm in ("青葉区", "宮城野区", "若林区", "太白区", "泉区"):
            alt = ("04", ("仙台市" + district).replace(" ", ""))
            if alt in lookup:
                gkey = lookup[alt][0]
        if gkey is None and (pref_name, district) in EXPLICIT_OVERRIDES:
            gkey = EXPLICIT_OVERRIDES[(pref_name, district)]
        if gkey is None:
            unmatched.append({"year": year, "pref_code": pref_code, "pref_name": pref_name, "district": district})
        else:
            crosswalk[(pref_code, district)] = gkey
    return crosswalk, unmatched


def build_year(source: Path, geo_light: Path, year: int, votes_path: Path, totals_path: Path, report: dict):
    districts = collect_districts(votes_path)
    crosswalk, unmatched = build_crosswalk(geo_light, year, districts)
    report[f"{year}_districts"] = len(districts)
    report[f"{year}_unmatched_districts"] = unmatched
    if unmatched:
        raise SystemExit(f"[FATAL] {year}: 地図に結合できない開票区があります: {unmatched}")

    cand_sum = defaultdict(lambda: Decimal("0"))
    cand_special = {}
    national_votes = defaultdict(lambda: Decimal("0"))
    party_name_sum = defaultdict(lambda: Decimal("0"))
    cand_name = {}
    special_candidates = {}
    n_candidate_rows = n_party_name_rows = 0

    with open(votes_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["vote_type"] == "candidate" and row.get("candidate_is_special") == "1" and row["candidate"]:
                special_candidates[(row["party"], row["candidate_number"])] = row["candidate"]
                # candidate_is_special は use_for_sum==0 の行にしか現れないため、
                # candidate_master向けのフラグ・氏名は行スコープのフィルタより前に(無条件で)記録する。
                skey = (year, row["party"], row["candidate_number"])
                cand_special[skey] = 1
                if skey not in cand_name:
                    cand_name[skey] = row["candidate"]
            if row["row_scope"] != "district" or row["use_for_sum"] != "1":
                continue
            pref_code, district = row["prefecture_code"], row["district"]
            gkey = crosswalk[(pref_code, district)]
            party = row["party"]
            v = to_decimal(row["votes"])
            if row["vote_type"] == "candidate":
                cnum = row["candidate_number"]
                ckey = (year, party, cnum)
                cand_sum[(gkey, party, cnum)] += v
                national_votes[ckey] += v
                if ckey not in cand_special:
                    cand_special[ckey] = 0
                if ckey not in cand_name and row["candidate"]:
                    cand_name[ckey] = row["candidate"]
                n_candidate_rows += 1
            elif row["vote_type"] == "party_name":
                party_name_sum[(gkey, party)] += v
                n_party_name_rows += 1

    party_total = defaultdict(lambda: Decimal("0"))
    candidate_sum_official = defaultdict(lambda: Decimal("0"))
    totals_districts = collect_districts(totals_path)
    totals_crosswalk, totals_unmatched = build_crosswalk(geo_light, year, totals_districts)
    report[f"{year}_totals_unmatched_districts"] = totals_unmatched
    if totals_unmatched:
        raise SystemExit(f"[FATAL] {year}: totals側で地図に結合できない開票区: {totals_unmatched}")

    n_totals_rows = 0
    with open(totals_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["row_scope"] != "district" or row["use_for_sum"] != "1":
                continue
            gkey = totals_crosswalk[(row["prefecture_code"], row["district"])]
            party = row["party"]
            v = to_decimal(row["votes"])
            if row["vote_type"] == "party_total":
                party_total[(gkey, party)] += v
                n_totals_rows += 1
            elif row["vote_type"] == "candidate_sum":
                candidate_sum_official[(gkey, party)] += v
                n_totals_rows += 1

    report[f"{year}_n_candidate_rows"] = n_candidate_rows
    report[f"{year}_n_party_name_rows"] = n_party_name_rows
    report[f"{year}_n_totals_rows"] = n_totals_rows

    # ---- 検算(指示書13章) ----
    cand_sum_by_party = defaultdict(lambda: Decimal("0"))
    for (gkey, party, _cnum), v in cand_sum.items():
        cand_sum_by_party[(gkey, party)] += v
    mism_cs = []
    for key in set(cand_sum_by_party) | set(candidate_sum_official):
        a, b = cand_sum_by_party.get(key, Decimal("0")), candidate_sum_official.get(key, Decimal("0"))
        if abs(a - b) > Decimal("0.001"):
            mism_cs.append([key, str(a), str(b)])
    report[f"{year}_mismatch_candidate_sum_vs_official"] = len(mism_cs)
    if mism_cs:
        report[f"{year}_mismatch_candidate_sum_vs_official_sample"] = mism_cs[:20]

    mism_pt = []
    for key in set(party_total) | set(candidate_sum_official) | set(party_name_sum):
        pn, cs, pt = party_name_sum.get(key, Decimal("0")), candidate_sum_official.get(key, Decimal("0")), party_total.get(key, Decimal("0"))
        if abs((pn + cs) - pt) > Decimal("0.001"):
            mism_pt.append([key, str(pn), str(cs), str(pt)])
    report[f"{year}_mismatch_party_total"] = len(mism_pt)
    if mism_pt:
        report[f"{year}_mismatch_party_total_sample"] = mism_pt[:20]

    if mism_cs or mism_pt:
        raise SystemExit(f"[FATAL] {year}: 検算NGがあります。candidate_sum={len(mism_cs)}件, party_total={len(mism_pt)}件")

    valid_votes = defaultdict(lambda: Decimal("0"))
    for (gkey, _party), v in party_total.items():
        valid_votes[gkey] += v

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with open(PROCESSED_DIR / f"candidate_votes_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "geometry_key", "party", "candidate_number", "candidate", "candidate_is_special", "votes"])
        for (gkey, party, cnum), v in sorted(cand_sum.items()):
            ckey = (year, party, cnum)
            w.writerow([year, gkey, party, cnum, cand_name.get(ckey, ""), cand_special.get(ckey, 0), format(v.quantize(Decimal("0.001")), "f")])

    with open(PROCESSED_DIR / f"party_totals_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "geometry_key", "party", "party_total", "candidate_sum", "party_name_votes"])
        for gkey, party in sorted(set(party_total) | set(candidate_sum_official) | set(party_name_sum)):
            w.writerow([
                year, gkey, party,
                format(party_total.get((gkey, party), Decimal("0")).quantize(Decimal("0.001")), "f"),
                format(candidate_sum_official.get((gkey, party), Decimal("0")).quantize(Decimal("0.001")), "f"),
                format(party_name_sum.get((gkey, party), Decimal("0")).quantize(Decimal("0.001")), "f"),
            ])

    with open(PROCESSED_DIR / f"municipality_valid_votes_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "geometry_key", "valid_votes"])
        for gkey, v in sorted(valid_votes.items()):
            w.writerow([year, gkey, format(v.quantize(Decimal("0.001")), "f")])

    with open(PROCESSED_DIR / f"special_candidates_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "party", "candidate_number", "candidate"])
        for (party, cnum), name in sorted(special_candidates.items()):
            w.writerow([year, party, cnum, name])

    # geo master(全geometry。選挙結果が無いものも含める)
    _, by_key = load_master(geo_light, year)
    with open(PROCESSED_DIR / f"municipality_geo_master_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "geometry_key", "pref_code", "pref_name", "display_name", "has_election_data"])
        for gkey, row in sorted(by_key.items()):
            w.writerow([year, gkey, row["pref_code"], row["pref_name"], row["display_name"].replace(" ", ""), int(gkey in valid_votes)])

    with open(PROCESSED_DIR / f"crosswalk_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "prefecture_code", "district", "geometry_key"])
        for (pref_code, district), gkey in sorted(crosswalk.items()):
            w.writerow([year, pref_code, district, gkey])

    return {"national_votes": national_votes, "cand_name": cand_name, "cand_special": cand_special}


def build_candidate_master(nat_2025, nat_2022):
    with open(PROCESSED_DIR / "candidate_master.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "party", "candidate_number", "candidate", "candidate_is_special", "national_votes"])
        for year, nat in [(2025, nat_2025), (2022, nat_2022)]:
            for (y, party, cnum), v in sorted(nat["national_votes"].items()):
                ckey = (y, party, cnum)
                w.writerow([y, party, cnum, nat["cand_name"].get(ckey, ""), nat["cand_special"].get(ckey, 0), format(v.quantize(Decimal("0.001")), "f")])


def copy_geo_web_and_masters(geo_light: Path):
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    for fn in ["japan_2022_web.geojson", "japan_2025_web.geojson", "prefectures.geojson"]:
        shutil.copy(geo_light / "geo" / fn, GEO_DIR / fn)


def split_detail_by_prefecture(detail_dir: Path, year: int):
    out_dir = GEO_DIR / "detail" / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = detail_dir / f"japan_{year}_detail.geojson"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    by_pref = defaultdict(list)
    for feat in data["features"]:
        by_pref[feat["properties"]["pref_code"]].append(feat)
    for pref_code, feats in by_pref.items():
        with open(out_dir / f"{pref_code}.geojson", "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False)
    return len(by_pref)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="展開済みデータのルートディレクトリ")
    args = ap.parse_args()
    source = Path(args.source)

    geo_light = source / "geo_light"
    candidate_complete = source / "candidate_complete"
    proportional = source / "proportional" / "election_data"
    detail_2022 = source / "japan_2022_detail"
    detail_2025 = source / "japan_2025_detail"

    report = {}
    nat_2025 = build_year(
        source, geo_light, 2025,
        candidate_complete / "2025_votes_long_complete.csv",
        candidate_complete / "2025_totals_long_complete.csv",
        report,
    )
    nat_2022 = build_year(
        source, geo_light, 2022,
        proportional / "2022_votes_long.csv",
        proportional / "2022_totals_long.csv",
        report,
    )
    build_candidate_master(nat_2025, nat_2022)
    copy_geo_web_and_masters(geo_light)
    n_pref_2022 = split_detail_by_prefecture(detail_2022, 2022)
    n_pref_2025 = split_detail_by_prefecture(detail_2025, 2025)
    report["detail_prefectures_2022"] = n_pref_2022
    report["detail_prefectures_2025"] = n_pref_2025

    # 全国総得票の検算(2025は59,185,398.465と一致する必要がある)
    total_2025 = sum(
        Decimal(row["valid_votes"])
        for row in csv.DictReader(open(PROCESSED_DIR / "municipality_valid_votes_2025.csv", encoding="utf-8"))
    )
    report["2025_national_total_valid_votes"] = str(total_2025)
    expected = Decimal("59185398.465")
    if abs(total_2025 - expected) > Decimal("0.001"):
        raise SystemExit(f"[FATAL] 2025年全国総得票が一致しません: {total_2025} != {expected}")

    with open(PROCESSED_DIR / "build_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print("BUILD OK")
    print(json.dumps({k: v for k, v in report.items() if "sample" not in k and "unmatched_districts" not in k}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
