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
