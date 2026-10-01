from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://civicapi.org/api/v2"
USER_AGENT = "ElectionPortal/0.10.1 (+civicAPI attribution)"


class CivicAPIError(RuntimeError):
    pass


def _request(path: str, params: dict[str, Any] | None = None, timeout: float = 15.0):
    params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    url = f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,image/svg+xml,*/*"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").lower()
            status = getattr(resp, "status", 200)
    except Exception as exc:
        raise CivicAPIError(f"civicAPIへの接続に失敗しました: {exc}") from exc
    if status >= 400:
        raise CivicAPIError(f"civicAPI HTTP {status}")
    return body, content_type, url


def _request_json(path: str, params: dict[str, Any] | None = None, timeout: float = 15.0) -> Any:
    body, _, _ = _request(path, params=params, timeout=timeout)
    try:
        return json.loads(body.decode("utf-8-sig"))
    except Exception as exc:
        raise CivicAPIError("civicAPIのJSONを解析できませんでした") from exc


def get_status() -> dict[str, Any]:
    data = _request_json("status")
    return data if isinstance(data, dict) else {"status": str(data)}


def search_races(
    *,
    country: str = "US",
    province: str | None = None,
    district: str | None = None,
    election_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    query: str | None = None,
    limit: int = 5000,
) -> Any:
    return _request_json(
        "race/search",
        {
            "country": country,
            "province": province,
            "district": district,
            "election_type": election_type,
            "start_date": start_date,
            "end_date": end_date,
            "query": query,
            "limit": limit,
        },
    )


def get_race(race_id: str | int, *, precinct: bool = False, testdata: bool = False) -> Any:
    return _request_json(
        f"race/{race_id}",
        {
            "precinct": "true" if precinct else None,
            "testdata": "true" if testdata else None,
        },
    )


def get_race_history(race_id: str | int) -> Any:
    return _request_json(f"race/{race_id}/history")


def get_race_map_svg(race_id: str | int, *, format_name: str = "percentage", testdata: bool = False) -> str:
    body, content_type, _ = _request(
        f"race/{race_id}",
        {
            "generate_map": "true",
            "format": format_name,
            "testdata": "true" if testdata else None,
        },
    )
    text = body.decode("utf-8", errors="replace")
    # Some deployments may wrap a generated SVG in JSON. Accept both forms.
    if "json" in content_type or text.lstrip().startswith("{"):
        try:
            obj = json.loads(text)
            for key in ("svg", "map", "body", "_body"):
                if isinstance(obj, dict) and isinstance(obj.get(key), str) and "<svg" in obj[key]:
                    return obj[key]
        except Exception:
            pass
    if "<svg" not in text:
        raise CivicAPIError("このレースではSVG地図を取得できませんでした")
    return text


def _unwrap(obj: Any) -> Any:
    """Unwrap common API response envelopes without assuming one exact schema."""
    cur = obj
    for _ in range(3):
        if not isinstance(cur, dict):
            break
        moved = False
        for key in ("data", "result", "race"):
            val = cur.get(key)
            if isinstance(val, (dict, list)):
                cur = val
                moved = True
                break
        if not moved:
            break
    return cur


def extract_race_list(obj: Any) -> list[dict[str, Any]]:
    obj = _unwrap(obj)
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("races", "results", "items", "elections", "data"):
            val = obj.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        # A single race result is still useful.
        if any(k in obj for k in ("race_id", "id", "election_name", "candidates")):
            return [obj]
    return []


def extract_race_detail(obj: Any) -> dict[str, Any]:
    obj = _unwrap(obj)
    return obj if isinstance(obj, dict) else {}


def pick(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("en_US", "en", "name", "label", "value"):
            if value.get(key):
                return str(value[key])
        for v in value.values():
            if isinstance(v, str) and v.strip():
                return v
    return str(value)


def num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if not value:
                return None
        return float(value)
    except Exception:
        return None


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes", "y", "called", "winner"}


def race_id(race: dict[str, Any]) -> str:
    return str(pick(race, "race_id", "id", "raceId", default=""))


def race_name(race: dict[str, Any]) -> str:
    return text_value(pick(race, "election_name", "name", "race_name", "title", default=""))


US_STATE_ABBR = {
    "ALABAMA":"AL","ALASKA":"AK","ARIZONA":"AZ","ARKANSAS":"AR","CALIFORNIA":"CA","COLORADO":"CO","CONNECTICUT":"CT","DELAWARE":"DE","FLORIDA":"FL","GEORGIA":"GA","HAWAII":"HI","IDAHO":"ID","ILLINOIS":"IL","INDIANA":"IN","IOWA":"IA","KANSAS":"KS","KENTUCKY":"KY","LOUISIANA":"LA","MAINE":"ME","MARYLAND":"MD","MASSACHUSETTS":"MA","MICHIGAN":"MI","MINNESOTA":"MN","MISSISSIPPI":"MS","MISSOURI":"MO","MONTANA":"MT","NEBRASKA":"NE","NEVADA":"NV","NEW HAMPSHIRE":"NH","NEW JERSEY":"NJ","NEW MEXICO":"NM","NEW YORK":"NY","NORTH CAROLINA":"NC","NORTH DAKOTA":"ND","OHIO":"OH","OKLAHOMA":"OK","OREGON":"OR","PENNSYLVANIA":"PA","RHODE ISLAND":"RI","SOUTH CAROLINA":"SC","SOUTH DAKOTA":"SD","TENNESSEE":"TN","TEXAS":"TX","UTAH":"UT","VERMONT":"VT","VIRGINIA":"VA","WASHINGTON":"WA","WEST VIRGINIA":"WV","WISCONSIN":"WI","WYOMING":"WY","DISTRICT OF COLUMBIA":"DC"
}

def _state_abbr(value: Any) -> str:
    s = text_value(value).strip().upper()
    if s.startswith("US-") and len(s) >= 5:
        s = s[-2:]
    if len(s) == 2:
        return s
    return US_STATE_ABBR.get(s, "")

def province_code(race: dict[str, Any]) -> str:
    value = pick(race, "province", "state", "province_code", "state_code", default="")
    if isinstance(value, dict):
        value = pick(value, "code", "abbreviation", "iso", "name", default="")
    code = _state_abbr(value)
    if code:
        return code
    details = race.get("district_details") if isinstance(race.get("district_details"), dict) else {}
    code = _state_abbr(pick(details, "province", "state", "district_country", default=""))
    if code:
        return code
    # Last resort: infer the state from the race name itself.
    name = race_name(race).upper()
    for state_name, abbr in US_STATE_ABBR.items():
        if state_name in name:
            return abbr
    return ""


def election_type(race: dict[str, Any]) -> str:
    raw = text_value(pick(race, "election_type", "type", "race_type", default="")).lower()
    name = race_name(race).lower()
    combined = f"{raw} {name}"
    if "senate" in combined and "state senate" not in combined:
        return "Senate"
    if ("us house" in combined or "u.s. house" in combined or "congress" in combined or raw == "house") and "state house" not in combined:
        return "House"
    if "governor" in combined:
        return "Governor"
    return text_value(pick(race, "election_type", "type", default="Other")) or "Other"


def reporting_pct(race: dict[str, Any]) -> float | None:
    v = num(pick(race, "percent_reporting", "reporting", "reporting_percent", default=None))
    if v is None:
        return None
    if 0 <= v <= 1:
        v *= 100
    return max(0.0, min(100.0, v))


def candidates(race: dict[str, Any]) -> list[dict[str, Any]]:
    val = pick(race, "candidates", "candidate_results", "results", default=[])
    if isinstance(val, dict):
        val = val.get("candidates") or val.get("results") or list(val.values())
    return [x for x in val if isinstance(x, dict)] if isinstance(val, list) else []


def candidate_name(c: dict[str, Any]) -> str:
    return text_value(pick(c, "name", "candidate_name", "full_name", default="Unknown"))


def candidate_party(c: dict[str, Any]) -> str:
    return text_value(pick(c, "party", "party_name", "party_code", default=""))


def candidate_votes(c: dict[str, Any]) -> int | None:
    v = num(pick(c, "votes", "vote_count", "total_votes", default=None))
    return int(round(v)) if v is not None else None


def candidate_percent(c: dict[str, Any]) -> float | None:
    v = num(pick(c, "percent", "percentage", "vote_percent", default=None))
    if v is None:
        return None
    if 0 <= v <= 1:
        v *= 100
    return v


def candidate_called(c: dict[str, Any]) -> bool:
    return any(bool_value(pick(c, key, default=False)) for key in ("winner", "called", "projected_winner", "is_winner"))


def candidate_incumbent(c: dict[str, Any]) -> bool:
    return bool_value(pick(c, "incumbent", "is_incumbent", default=False))


def party_bucket(party: str) -> str:
    p = party.strip().upper()
    if p in {"DEM", "D", "DEMOCRATIC", "DEMOCRAT"} or "DEMOCR" in p:
        return "DEM"
    if p in {"REP", "R", "REPUBLICAN"} or "REPUBLIC" in p:
        return "REP"
    return "OTH"


def leader(race: dict[str, Any]) -> dict[str, Any] | None:
    cs = candidates(race)
    if not cs:
        return None
    called = [c for c in cs if candidate_called(c)]
    if called:
        return called[0]
    scored = [c for c in cs if candidate_votes(c) is not None or candidate_percent(c) is not None]
    if not scored:
        return None
    return max(
        scored,
        key=lambda c: (
            candidate_votes(c) if candidate_votes(c) is not None else -1,
            candidate_percent(c) if candidate_percent(c) is not None else -1.0,
        ),
    )


def snapshot(race: dict[str, Any]) -> dict[str, Any]:
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "race_id": race_id(race),
        "reporting_pct": reporting_pct(race),
        "candidates": [
            {
                "name": candidate_name(c),
                "party": candidate_party(c),
                "votes": candidate_votes(c),
                "percent": candidate_percent(c),
                "called": candidate_called(c),
            }
            for c in candidates(race)
        ],
    }
