"""
2026年米国中間選挙ポータル用のデータ取得モジュール。

データソースは civicAPI (https://civicapi.org) の無料・認証不要のレース検索API。
公式選管の発表ではない非公式のサードパーティAPIであるため、取得した結果はあくまで
参考情報として扱う。ネットワークエラーやAPI側の不調時は例外を投げるだけにして、
呼び出し側(us_midterms.py)でセッションキャッシュへのフォールバックを行う。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_URL = "https://civicapi.org/api/v2"
TIMEOUT = 12
ELECTION_DATE_2026 = "2026-11-03"

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"


class FetchError(Exception):
    pass


def _get(path: str, params: dict | None = None, timeout: int = TIMEOUT):
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{BASE_URL}{path}{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "okinawa-election-portal/1.0 (+us-midterms-page)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"{url} の取得に失敗しました: {exc}") from exc
    try:
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"{url} のJSON解析に失敗しました: {exc}") from exc


def api_status() -> dict:
    return _get("/status")


def search_races(query: str, limit: int = 60, offset: int = 0) -> list[dict]:
    data = _get("/race/search", {"query": query, "limit": limit, "offset": offset})
    if isinstance(data, dict):
        return data.get("races") or data.get("results") or []
    return []


def is_general_2026(race: dict) -> bool:
    return (
        str(race.get("election_type", "")).strip().lower() == "general"
        and str(race.get("election_date", "")).startswith(ELECTION_DATE_2026)
    )


def load_states_config() -> list[dict]:
    with open(DATA_DIR / "us_states_2026.json", encoding="utf-8") as f:
        return json.load(f)["states"]


def load_house_watchlist() -> list[dict]:
    with open(DATA_DIR / "us_house_watchlist_2026.json", encoding="utf-8") as f:
        return json.load(f)["districts"]


def _best_match(races: list[dict], race_type: str) -> dict | None:
    candidates = [
        r for r in races
        if str(r.get("type", "")).strip().lower() == race_type.lower() and is_general_2026(r)
    ]
    if not candidates:
        return None
    # 複数ヒットした場合は開票率が高い(＝より新しい/本選に近い)ものを優先
    candidates.sort(key=lambda r: r.get("percent_reporting") or 0, reverse=True)
    return candidates[0]


def _fetch_one_statewide(code: str, name: str, race_type: str, query_suffix: str) -> tuple[str, dict | None, str | None]:
    try:
        races = search_races(f"{name} {query_suffix}", limit=20)
    except FetchError as exc:
        return code, None, str(exc)
    return code, _best_match(races, race_type), None


def get_senate_races(states: list[dict], max_workers: int = 8) -> tuple[dict, list[str]]:
    targets = [s for s in states if s.get("senate_2026")]
    results: dict[str, dict] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(_fetch_one_statewide, s["code"], s["name"], "US Senate", "US Senate")
            for s in targets
        ]
        for fut in as_completed(futures):
            code, race, err = fut.result()
            if race is not None:
                results[code] = race
            elif err:
                errors.append(f"{code}: {err}")
    return results, errors


def get_governor_races(states: list[dict], max_workers: int = 8) -> tuple[dict, list[str]]:
    targets = [s for s in states if s.get("governor_2026")]
    results: dict[str, dict] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(_fetch_one_statewide, s["code"], s["name"], "Governor", "Governor")
            for s in targets
        ]
        for fut in as_completed(futures):
            code, race, err = fut.result()
            if race is not None:
                results[code] = race
            elif err:
                errors.append(f"{code}: {err}")
    return results, errors


def _fetch_house_for_state(code: str, name: str) -> tuple[str, list[dict], str | None]:
    try:
        races = search_races(f"{name} US House", limit=60)
    except FetchError as exc:
        return code, [], str(exc)
    generals = [r for r in races if str(r.get("type", "")).strip().lower() == "us house" and is_general_2026(r)]
    return code, generals, None


def get_all_house_races(states: list[dict], max_workers: int = 12) -> tuple[dict, list[str]]:
    """全50州について『{州名} US House』を検索し、district(例:'PA-08')をキーに全選挙区分の
    レースをまとめて返す。BALANCE OF POWER(下院)の集計に使う。一部の州の取得に失敗しても、
    他の州の結果はそのまま返す(エラーはerrorsに集約)。"""
    by_district: dict[str, dict] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_fetch_house_for_state, s["code"], s["name"]) for s in states]
        for fut in as_completed(futures):
            code, races, err = fut.result()
            if err:
                errors.append(f"{code}: {err}")
                continue
            for r in races:
                district = r.get("district") or ""
                if district:
                    by_district[district] = r
    return by_district, errors


def get_house_watchlist_races(watchlist: list[dict], max_workers: int = 8) -> tuple[dict, list[str]]:
    """ウォッチリストに含まれる州についてまとめて検索し、district(例: 'PA-08')をキーに返す。"""
    state_names = {}
    for entry in watchlist:
        state_names[entry["code"]] = entry["state"]

    by_district: dict[str, dict] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_fetch_house_for_state, code, name) for code, name in state_names.items()]
        for fut in as_completed(futures):
            code, races, err = fut.result()
            if err:
                errors.append(f"{code}: {err}")
                continue
            for r in races:
                district = r.get("district") or ""
                if district:
                    by_district[district] = r

    wanted_districts = {e["district"] for e in watchlist}
    return {d: by_district[d] for d in wanted_districts if d in by_district}, errors


def leading_party(race: dict) -> str | None:
    """候補者のうちリードしている(得票数最大の)候補の政党名を返す。データが無ければNone。"""
    candidates = race.get("candidates") or []
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.get("votes") or 0)
    if (best.get("votes") or 0) == 0 and not any((c.get("winner") for c in candidates)):
        # 投票開始前(全員0票)はまだ「リード」とは言えない
        return None
    winner = next((c for c in candidates if c.get("winner")), None)
    if winner:
        return winner.get("party")
    return best.get("party")


def party_bucket(party: str | None) -> str:
    """政党名を 'dem' / 'rep' / 'other' の3種類に正規化する。"""
    if not party:
        return "other"
    p = party.strip().lower()
    if p.startswith("dem"):
        return "dem"
    if p.startswith("rep") or p.startswith("gop"):
        return "rep"
    return "other"


def sorted_candidates(race: dict) -> list[dict]:
    return sorted(race.get("candidates") or [], key=lambda c: c.get("votes") or 0, reverse=True)


def race_status(race: dict) -> str:
    """'called' / 'leading' / 'not_reporting' / 'no_data' のいずれかを返す。

    APIのcandidates[].winnerフラグが立っている場合のみ「当確(called)」として扱う。
    winnerが立っていなければ、1位候補がいても単なる「リード(leading)」に留める。
    全候補が0票(かつwinnerも無い)場合は「開票前(not_reporting)」とする。
    """
    candidates = race.get("candidates") or []
    if not candidates:
        return "no_data"
    if any(c.get("winner") for c in candidates):
        return "called"
    total_votes = sum((c.get("votes") or 0) for c in candidates)
    if total_votes <= 0:
        return "not_reporting"
    return "leading"


def race_margin(race: dict) -> dict | None:
    """上位2候補の票差・pt差を返す。開票前やデータ不足ならNone。

    戻り値: {"leader": cand, "runner_up": cand, "vote_diff": int, "pct_diff": float}
    """
    candidates = sorted_candidates(race)
    if len(candidates) < 2:
        return None
    leader, runner_up = candidates[0], candidates[1]
    if (leader.get("votes") or 0) <= 0 and (runner_up.get("votes") or 0) <= 0:
        return None
    vote_diff = (leader.get("votes") or 0) - (runner_up.get("votes") or 0)
    pct_diff = (leader.get("percent") or 0) - (runner_up.get("percent") or 0)
    return {"leader": leader, "runner_up": runner_up, "vote_diff": vote_diff, "pct_diff": pct_diff}


def map_score(race: dict) -> int:
    """全米マップ用の5段階スコア。-2=DEM CALL -1=DEM LEAD 0=UNCALLED/NO DATA +1=REP LEAD +2=REP CALL"""
    status = race_status(race)
    if status in ("no_data", "not_reporting"):
        return 0
    party = leading_party(race)
    bucket = party_bucket(party)
    if bucket == "dem":
        return -2 if status == "called" else -1
    if bucket == "rep":
        return 2 if status == "called" else 1
    return 0


def load_holdover_config() -> dict:
    with open(DATA_DIR / "us_congress_holdover_2026.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# DESIGN PREVIEW DATA（本番開票前にビジュアルを確認するためのダミーデータ）
#
# 実在候補者の実際の得票として誤認されないよう、候補者名は
# 「(州名) Dem Nominee」のような明示的な仮名のみを使う。
# 乱数はシード固定で、ページを再読み込みしても見た目が安定するようにする。
# ---------------------------------------------------------------------------
import random as _random


def _preview_race(seed_key: str, label: str, race_type: str, dem_name: str, rep_name: str) -> dict:
    rng = _random.Random(seed_key)
    # 開票率: 0%(開票前) / 途中 / 100%(当確)をバランスよく混在させる
    bucket = rng.random()
    if bucket < 0.2:
        pct_reporting = 0
    elif bucket < 0.75:
        pct_reporting = round(rng.uniform(15, 95), 1)
    else:
        pct_reporting = 100.0

    if pct_reporting == 0:
        dem_votes = rep_votes = 0
        dem_pct = rep_pct = 0.0
        dem_winner = rep_winner = False
    else:
        dem_share = rng.uniform(0.40, 0.60)
        total_votes = int(rng.uniform(80_000, 2_200_000) * (pct_reporting / 100))
        dem_votes = int(total_votes * dem_share)
        rep_votes = total_votes - dem_votes
        dem_pct = round(100 * dem_share, 1)
        rep_pct = round(100 - dem_pct, 1)
        margin = abs(dem_pct - rep_pct)
        called = pct_reporting >= 97 and margin >= 1.5
        dem_winner = called and dem_votes > rep_votes
        rep_winner = called and rep_votes > dem_votes

    return {
        "type": race_type,
        "election_type": "General",
        "election_date": f"{ELECTION_DATE_2026}T05:00:00.000Z",
        "election_name": label,
        "percent_reporting": pct_reporting,
        "district": None,
        "candidates": [
            {"name": dem_name, "party": "Democratic", "votes": dem_votes, "percent": dem_pct, "winner": dem_winner},
            {"name": rep_name, "party": "Republican", "votes": rep_votes, "percent": rep_pct, "winner": rep_winner},
        ],
    }


def senate_balance(senate_races: dict, holdover: dict) -> dict:
    called_dem = called_rep = called_other = 0
    for r in senate_races.values():
        if race_status(r) != "called":
            continue
        bucket = party_bucket(leading_party(r))
        if bucket == "dem":
            called_dem += 1
        elif bucket == "rep":
            called_rep += 1
        else:
            called_other += 1
    total = holdover.get("total_seats", 100)
    up = holdover.get("up_in_2026", len(senate_races))
    dem_total = holdover.get("holdover_dem_caucus", 0) + called_dem
    rep_total = holdover.get("holdover_rep", 0) + called_rep
    other_total = holdover.get("holdover_other", 0) + called_other
    uncalled = max(0, total - dem_total - rep_total - other_total)
    return {
        "total": total, "up": up,
        "dem_total": dem_total, "rep_total": rep_total,
        "other_total": other_total, "uncalled": uncalled,
        "called_dem": called_dem, "called_rep": called_rep, "called_other": called_other,
    }


def house_balance(all_house_races: dict, holdover: dict) -> dict:
    called_dem = called_rep = called_other = 0
    for r in all_house_races.values():
        if race_status(r) != "called":
            continue
        bucket = party_bucket(leading_party(r))
        if bucket == "dem":
            called_dem += 1
        elif bucket == "rep":
            called_rep += 1
        else:
            called_other += 1
    total = holdover.get("total_seats", 435)
    dem_total = holdover.get("holdover_dem", 0) + called_dem
    rep_total = holdover.get("holdover_rep", 0) + called_rep
    other_total = called_other
    uncalled = max(0, total - dem_total - rep_total - other_total - holdover.get("holdover_vacant", 0))
    return {
        "total": total,
        "dem_total": dem_total, "rep_total": rep_total,
        "other_total": other_total, "uncalled": uncalled,
        "called_dem": called_dem, "called_rep": called_rep, "called_other": called_other,
        "races_tracked": len(all_house_races),
    }


def governor_summary(governor_races: dict) -> dict:
    called_dem = called_rep = called_other = leading = not_reporting = 0
    for r in governor_races.values():
        status = race_status(r)
        if status == "called":
            bucket = party_bucket(leading_party(r))
            if bucket == "dem":
                called_dem += 1
            elif bucket == "rep":
                called_rep += 1
            else:
                called_other += 1
        elif status == "leading":
            leading += 1
        else:
            not_reporting += 1
    return {
        "called_dem": called_dem, "called_rep": called_rep, "called_other": called_other,
        "leading": leading, "not_reporting": not_reporting, "total": len(governor_races),
    }


def build_preview_data() -> tuple[dict, dict, dict]:
    """DESIGN PREVIEW DATA一式(senate_races, governor_races, house_races)を生成する。"""
    states = load_states_config()
    watchlist = load_house_watchlist()

    senate_races = {}
    for s in states:
        if not s.get("senate_2026"):
            continue
        code = s["code"]
        senate_races[code] = _preview_race(
            f"senate-{code}", f"{s['name']} US Senate",
            "US Senate", f"{code} Dem Nominee", f"{code} Rep Nominee",
        )

    governor_races = {}
    for s in states:
        if not s.get("governor_2026"):
            continue
        code = s["code"]
        governor_races[code] = _preview_race(
            f"governor-{code}", f"{s['name']} Governor",
            "Governor", f"{code} Dem Nominee", f"{code} Rep Nominee",
        )

    house_races = {}
    for entry in watchlist:
        district = entry["district"]
        race = _preview_race(
            f"house-{district}", f"{entry['state']} {district} US House",
            "US House", f"{district} Dem Nominee", f"{district} Rep Nominee",
        )
        race["district"] = district
        house_races[district] = race

    return senate_races, governor_races, house_races
