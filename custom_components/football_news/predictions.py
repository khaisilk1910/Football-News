"""Independent Last Man Standing and Acca League competition management.

The engines are pure-Python, reusable without Home Assistant. All competition
administration is authenticated in Home Assistant. There are deliberately no
unauthenticated 'secret link' endpoints or payment-processing integrations.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


def utcnow():
    return datetime.now(timezone.utc)


def deadline_passed(deadline: str, now=None) -> bool:
    try:
        value = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("Deadline requires timezone")
        return (now or utcnow()) >= value
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid deadline (ISO8601 with timezone required)") from exc


def new_competition(kind: str, title: str, league: str) -> dict:
    if kind not in {"lms", "acca"} or not (1 <= len(title.strip()) <= 80):
        raise ValueError("Invalid competition type or title")
    return {"id": uuid4().hex[:12], "kind": kind, "title": title.strip(),
            "league": league, "created": utcnow().isoformat(), "players": {},
            "rounds": {}, "results": {}, "history": []}


def add_player(comp: dict, name: str) -> str:
    if not isinstance(name, str) or not (1 <= len(name.strip()) <= 70):
        raise ValueError("Invalid player name")
    player_id = uuid4().hex[:12]
    comp["players"][player_id] = {"name": name.strip(), "paid": 0.0,
                                   "buybacks": 0, "active": True}
    return player_id


def configure_round(comp: dict, round_id: str, deadline: str, fixture_ids: list[str]):
    if not round_id or len(round_id) > 30 or not round_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid round ID")
    if deadline_passed(deadline):
        raise ValueError("Deadline must be in the future")
    if not (1 <= len(fixture_ids) <= 40) or any(not fid.isascii() or not fid.isdigit() for fid in fixture_ids):
        raise ValueError("Provide 1-40 numeric fixture IDs")
    if len(set(fixture_ids)) != len(fixture_ids):
        raise ValueError("Duplicate fixtures")
    if round_id in comp["rounds"]:
        raise ValueError("Round already exists; existing picks cannot be reset")
    comp["rounds"][round_id] = {"deadline": deadline, "fixtures": fixture_ids,
                                  "picks": {}, "outcomes": {}, "complete": False}


def submit_pick(comp: dict, round_id: str, player_id: str, picks: list[dict], now=None):
    if player_id not in comp["players"] or round_id not in comp["rounds"]:
        raise ValueError("Unknown player or round")
    round_data = comp["rounds"][round_id]
    if deadline_passed(round_data["deadline"], now):
        raise ValueError("The selection deadline has passed")
    if not comp["players"][player_id]["active"]:
        raise ValueError("Player has been eliminated")
    expected = 1 if comp["kind"] == "lms" else 2
    if len(picks) != expected:
        raise ValueError(f"Exactly {expected} pick(s) required")
    fixture_ids = [str(p.get("fixture_id", "")) for p in picks]
    if len(set(fixture_ids)) != len(fixture_ids) or any(fid not in round_data["fixtures"] for fid in fixture_ids):
        raise ValueError("Picks must refer to distinct fixtures in the configured round")
    if comp["kind"] == "lms":
        team_id = str(picks[0].get("team_id", ""))
        if not team_id.isascii() or not team_id.isdigit():
            raise ValueError("Choose a numeric team ID")
        for other_id, other_round in comp["rounds"].items():
            if other_id == round_id:
                continue
            if any(str(p.get("team_id")) == team_id for p in other_round["picks"].get(player_id, [])):
                raise ValueError("LMS club cannot be picked in another round")
        clean = [{"fixture_id": fixture_ids[0], "team_id": team_id}]
    else:
        if any(str(p.get("outcome")) not in {"H", "D", "A"} for p in picks):
            raise ValueError("Acca outcomes must be H (home), D (draw), or A (away)")
        clean = [{"fixture_id": fid, "outcome": str(p["outcome"])} for fid, p in zip(fixture_ids, picks, strict=True)]
    round_data["picks"][player_id] = clean


def fixture_outcome(fixture: dict) -> str | None:
    if fixture.get("state") != "post":
        return None
    home = fixture.get("home") or {}
    away = fixture.get("away") or {}
    a, b = home.get("score"), away.get("score")
    if type(a) is not int or type(b) is not int:
        return None
    return "H" if a > b else "A" if b > a else "D"


def settle(comp: dict, fixtures: list[dict]) -> bool:
    """Idempotently score only rounds whose complete, verified results exist.

    3/1/0 for Acca: both predictions right -> 3, one -> 1, none -> 0.
    LMS: a picked team must win its fixture, draws eliminate the player.
    """
    fixture_map = {str(f.get("id")): f for f in fixtures}
    changed = False
    for round_id, round_data in comp["rounds"].items():
        if round_data["complete"] or not deadline_passed(round_data["deadline"]):
            continue
        if any(fixture_outcome(fixture_map.get(fid, {})) is None for fid in round_data["fixtures"]):
            continue
        results = {}
        for player_id, player in comp["players"].items():
            picks = round_data["picks"].get(player_id, [])
            if comp["kind"] == "lms":
                if not picks:
                    survived = False
                else:
                    match = fixture_map[picks[0]["fixture_id"]]
                    outcome = fixture_outcome(match)
                    winner = ((match.get("home") or {}).get("id") if outcome == "H" else
                              (match.get("away") or {}).get("id") if outcome == "A" else None)
                    survived = str(winner) == str(picks[0]["team_id"]) if winner else False
                if not survived and player["active"]:
                    player["active"] = False
                results[player_id] = {"survived": survived}
            else:
                correct = sum(fixture_outcome(fixture_map[p["fixture_id"]]) == p["outcome"] for p in picks)
                results[player_id] = {"correct": correct, "points": {0: 0, 1: 1, 2: 3}[correct]}
        round_data["outcomes"] = results
        round_data["complete"] = True
        comp["history"].append({"round_id": round_id, "scored_at": utcnow().isoformat()})
        changed = True
    return changed


def standings(comp: dict) -> list[dict]:
    output = []
    for player_id, player in comp["players"].items():
        total = sum(int(r["outcomes"].get(player_id, {}).get("points", 0))
                    for r in comp["rounds"].values())
        survived = sum(bool(r["outcomes"].get(player_id, {}).get("survived", False))
                       for r in comp["rounds"].values())
        output.append({"id": player_id, "name": player["name"], "active": player["active"],
                       "points": total, "survived_rounds": survived,
                       "paid": player["paid"], "buybacks": player["buybacks"]})
    output.sort(key=lambda x: (-x["points"], -x["survived_rounds"], x["name"].casefold()))
    return output


def public_snapshot(comp: dict, include_pending: bool = False) -> dict:
    """A private dashboard snapshot; pending selections withheld by default."""
    result = deepcopy(comp)
    if not include_pending:
        for round_data in result["rounds"].values():
            if not deadline_passed(round_data["deadline"]):
                round_data["picks"] = {}
    result["standings"] = standings(comp)
    result["prize_fund"] = round(sum(p["paid"] for p in comp["players"].values()), 2)
    return result


class PredictionsStore:
    """Lazy HA Store ensures no disk reads or network fetch during startup."""

    def __init__(self, hass):
        from homeassistant.helpers.storage import Store
        self._store = Store(hass, 1, "football_news_predictions")
        self._data = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    async def _load(self):
        if not self._loaded:
            saved = await self._store.async_load()
            self._data = saved if isinstance(saved, dict) else {}
            self._loaded = True

    async def all(self) -> list[dict]:
        async with self._lock:
            await self._load()
            return [public_snapshot(item) for item in self._data.values()]

    async def mutate(self, operation: str, args: dict):
        async with self._lock:
            await self._load()
            comp = self._data.get(args.get("competition_id"))
            if operation == "create":
                comp = new_competition(args["kind"], args["title"], args["league"])
                self._data[comp["id"]] = comp
                output = {"competition_id": comp["id"]}
            elif comp is None:
                raise ValueError("Competition not found")
            elif operation == "add_player":
                output = {"player_id": add_player(comp, args["player_name"])}
            elif operation == "round":
                configure_round(comp, args["round_id"], args["deadline"], args["fixture_ids"])
                output = {"round_id": args["round_id"]}
            elif operation == "pick":
                submit_pick(comp, args["round_id"], args["player_id"], args["picks"])
                output = {"accepted": True}
            elif operation == "payment":
                player = comp["players"].get(args["player_id"])
                if player is None:
                    raise ValueError("Unknown player")
                amount = float(args["amount"])
                if not 0 <= amount <= 1000000:
                    raise ValueError("Invalid payment amount")
                player["paid"] = round(amount, 2)
                output = {"accepted": True}
            elif operation == "buyback":
                if comp["kind"] != "lms":
                    raise ValueError("Buyback only applies to LMS")
                player = comp["players"].get(args["player_id"])
                if player is None or player["active"]:
                    raise ValueError("Buyback only applies to an eliminated player")
                player["active"] = True
                player["buybacks"] += 1
                output = {"accepted": True}
            else:
                raise ValueError("Unknown competition action")
            await self._store.async_save(self._data)
            return output

    async def auto_settle(self, fixtures: list[dict]):
        async with self._lock:
            await self._load()
            changed = any([settle(comp, fixtures) for comp in self._data.values()])
            if changed:
                await self._store.async_save(self._data)
