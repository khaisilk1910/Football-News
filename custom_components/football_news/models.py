"""Pure functions for normalizing upstream football records.

Upstream feeds are not official HA APIs. Be defensive: missing fields never
silently become an invented score, scorekeeper, or kickoff time.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _url(value: Any) -> str:
    url = _text(value)
    split = urlsplit(url)
    return url if split.scheme == "https" and split.netloc else ""


def normalize_fixture(event: dict, league: str) -> dict | None:
    """Convert ESPN scoreboard event to a compact, stable shape."""
    event = _dict(event)
    event_id = _text(event.get("id"))
    competition = _dict((_list(event.get("competitions")) or [{}])[0])
    competitors = [_dict(c) for c in _list(competition.get("competitors"))]
    home = next((item for item in competitors if item.get("homeAway") == "home"), {})
    away = next((item for item in competitors if item.get("homeAway") == "away"), {})
    if not event_id or not home or not away:
        return None

    def team_of(item: dict) -> dict:
        team = _dict(item.get("team"))
        first_logo = _dict((_list(team.get("logos")) or [{}])[0])
        logo = team.get("logo") or first_logo.get("href")
        raw_score = item.get("score")
        if isinstance(raw_score, dict):
            raw_score = raw_score.get("value", raw_score.get("displayValue"))
        return {
            "id": _text(team.get("id")),
            "name": _text(team.get("displayName") or team.get("shortDisplayName") or team.get("name")),
            "short_name": _text(team.get("shortDisplayName") or team.get("abbreviation")),
            "logo": _url(logo),
            "score": _int(raw_score),
        }

    status = _dict(_dict(event.get("status")).get("type"))
    if not status:
        status = _dict(_dict(competition.get("status")).get("type"))
    state = _text(status.get("state") or "pre").lower()
    state = state if state in {"pre", "in", "post"} else "pre"
    kickoff = _text(event.get("date") or competition.get("date"))
    try:
        dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        kickoff = dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        kickoff = ""
    venue = _dict(competition.get("venue"))
    links = _list(event.get("links"))
    link = next((_url(_dict(x).get("href")) for x in links if _url(_dict(x).get("href"))), "")
    return {
        "id": event_id,
        "league": league,
        "name": _text(event.get("name")),
        "kickoff": kickoff,
        "state": state,
        "status": _text(status.get("shortDetail") or status.get("detail") or status.get("name")),
        "home": team_of(home),
        "away": team_of(away),
        "venue": _text(venue.get("fullName")),
        "link": link,
    }


def normalize_standings(payload: dict) -> list[dict]:
    """Read ESPN v2 standings, including both nested and flat presentations."""
    source = _dict(payload)
    roots = [source, *_list(source.get("children"))]
    rows: list[dict] = []
    for root in roots:
        entries = _list(_dict(_dict(root).get("standings")).get("entries"))
        for item in entries:
            item = _dict(item)
            team = _dict(item.get("team"))
            stats = {}
            for stat in _list(item.get("stats")):
                stat = _dict(stat)
                for key in (stat.get("name"), stat.get("abbreviation")):
                    if key:
                        stats[str(key).lower()] = stat.get("value", stat.get("displayValue"))
            def pick(*keys):
                for key in keys:
                    if stats.get(key) is not None and stats.get(key) != "":
                        return stats[key]
                return None
            rows.append({
                "id": _text(team.get("id")),
                "name": _text(team.get("displayName") or team.get("name")),
                "logo": _url(team.get("logos", [{}])[0].get("href") if isinstance(team.get("logos"), list) and team["logos"] else team.get("logo")),
                "played": _int(pick("gamesplayed", "gp")),
                "wins": _int(pick("wins", "w")),
                "draws": _int(pick("ties", "draws", "d")),
                "losses": _int(pick("losses", "l")),
                "points": _int(pick("points", "pts")),
                "difference": _int(pick("pointdifferential", "gd")),
                "position": _int(pick("rank", "rnk") if pick("rank", "rnk") is not None else item.get("rank")),
            })
    rows.sort(key=lambda item: (item["position"] is None, item["position"] or 999))
    return rows


def normalize_news(payload: dict, league: str) -> list[dict]:
    """Extract verifiable article titles and HTTPS URLs; never fabricate text."""
    articles = []
    for article in _list(_dict(payload).get("articles"))[:40]:
        article = _dict(article)
        links = _dict(article.get("links"))
        url = _url(_dict(links.get("web")).get("href") or article.get("link"))
        title = _text(article.get("headline") or article.get("title"))
        if not (url and title):
            continue
        articles.append({
            "id": _text(article.get("id") or url),
            "league": league,
            "title": title[:300],
            "description": _text(article.get("description"))[:600],
            "url": url,
            "published": _text(article.get("published") or article.get("lastModified")),
            "source": "ESPN",
        })
    return articles


def normalize_summary(payload: dict) -> dict:
    """Create a small, presentation-ready match detail without guessing stats."""
    payload = _dict(payload)
    game_info = _dict(payload.get("gameInfo"))
    venue = _dict(game_info.get("venue"))
    events = _list(payload.get("keyEvents")) or _list(payload.get("scoringPlays"))
    details = []
    for event in events[:60]:
        event = _dict(event)
        clock = _dict(event.get("clock"))
        event_type = _dict(event.get("type"))
        team = _dict(event.get("team"))
        description = _text(event.get("text") or event.get("description") or event.get("shortText")
                            or event_type.get("text") or event.get("displayValue"))
        if description:
            details.append({"minute": _text(clock.get("displayValue")),
                            "description": description[:350], "team": _text(team.get("displayName"))})
    teams = []
    for row in _list(_dict(payload.get("boxscore")).get("teams"))[:2]:
        row = _dict(row)
        team = _dict(row.get("team"))
        stats = []
        for stat in _list(row.get("statistics"))[:25]:
            stat = _dict(stat)
            label = _text(stat.get("label") or stat.get("name") or stat.get("abbreviation"))
            value = _text(stat.get("displayValue") if stat.get("displayValue") is not None else stat.get("value"))
            if label and value:
                stats.append({"label": label[:90], "value": value[:45]})
        if team.get("displayName"):
            teams.append({"name": _text(team.get("displayName")), "statistics": stats})
    return {"venue": _text(venue.get("fullName")), "attendance": _int(game_info.get("attendance")),
            "events": details, "teams": teams, "source": "ESPN"}
