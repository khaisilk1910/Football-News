"""Pure functions for normalizing upstream football records.

Upstream feeds are not official HA APIs. Be defensive: missing fields never
silently become an invented score, scorekeeper, or kickoff time.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
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



# ESPN athlete portraits are served from its CDN; no player images are stored
# or downloaded by the integration. IDs are ESPN athlete IDs, not team IDs.
def espn_athlete_photo(athlete: dict, player_id: str = "") -> str:
    """Prefer explicit ESPN headshots, then the ESPN CDN athlete-ID pattern.

    Never turn a name, arbitrary URL or non-numeric ID into a photo path.
    A CDN image may still 404; the frontend displays a local silhouette.
    """
    athlete = _dict(athlete)
    def candidate(value):
        if isinstance(value, dict):
            value = value.get("href") or value.get("url") or value.get("src")
        if not isinstance(value, str):
            return ""
        parsed = urlsplit(value)
        domain = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            domain == "espncdn.com" or domain.endswith(".espncdn.com") or
            domain == "espn.com" or domain.endswith(".espn.com")
        ):
            return ""
        return value
    for field in ("headshot", "photo", "image", "avatar", "images"):
        field_value = athlete.get(field)
        if isinstance(field_value, list):
            for entry in field_value[:5]:
                if photo := candidate(entry):
                    return photo
        elif photo := candidate(field_value):
            return photo
    identifier = _text(player_id or athlete.get("id"))
    if re.fullmatch(r"[0-9]{1,12}", identifier):
        return f"https://a.espncdn.com/i/headshots/soccer/players/full/{identifier}.png"
    return ""


def espn_player_id_from_profile(href: str) -> str:
    """Extract ESPN athlete ID from a genuine ESPN player profile link."""
    if not isinstance(href, str):
        return ""
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == "espn.com" or host.endswith(".espn.com")):
            return ""
    match = re.search(r"/soccer/player/(?:_/)?id/([0-9]{1,12})(?:/|$)", parsed.path)
    return match.group(1) if match else ""


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
    # ESPN may expose an explicit matchday/round number in different shapes.
    # Do not infer a round number from calendar dates.
    round_value = (competition.get("round") or competition.get("matchday") or
                   competition.get("week") or event.get("round") or event.get("matchday") or
                   event.get("week"))
    if isinstance(round_value, dict):
        round_value = round_value.get("number") or round_value.get("roundNumber") or round_value.get("value")
    round_number = _int(round_value)
    if round_number is not None and not 1 <= round_number <= 100:
        round_number = None
    return {
        "round": round_number,
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
                "goals_for": _int(pick("pointsfor", "goalsfor", "gf")),
                "goals_against": _int(pick("pointsagainst", "goalsagainst", "ga")),
                "form": _text(pick("streak", "form", "lastfive", "last5") or "")[:35],
                "position": _int(pick("rank", "rnk") if pick("rank", "rnk") is not None else item.get("rank")),
                "note": _text(_dict(item.get("note")).get("description") or item.get("note")
                               if isinstance(item.get("note"), str) else _dict(item.get("note")).get("description"))[:120],
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


def normalize_teams(payload: dict) -> list[dict]:
    """Read the nested ESPN sports/leagues/teams directory safely."""
    teams = []
    seen = set()
    sport_groups = _list(_dict(payload).get("sports"))
    for sport in sport_groups:
        for league in _list(_dict(sport).get("leagues")):
            for wrapper in _list(_dict(league).get("teams")):
                item = _dict(_dict(wrapper).get("team")) or _dict(wrapper)
                team_id = _text(item.get("id"))
                if not team_id or not team_id.isascii() or not team_id.isdigit() or team_id in seen:
                    continue
                name = _text(item.get("displayName") or item.get("name"))
                if not name:
                    continue
                seen.add(team_id)
                logos = _list(item.get("logos"))
                teams.append({"id": team_id, "name": name[:100],
                              "short_name": _text(item.get("shortDisplayName") or item.get("abbreviation")),
                              "logo": _url(_dict(logos[0]).get("href") if logos else item.get("logo"))})
    return sorted(teams, key=lambda x: x["name"].casefold())[:100]


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
            event_name = _text(event_type.get("text") or event_type.get("name") or
                               event_type.get("displayName") or event.get("typeText")).casefold()
            kind = ("goal" if "goal" in event_name else
                    "card" if "card" in event_name else
                    "substitution" if "substitution" in event_name else
                    "start" if "start" in event_name or "kickoff" in event_name else "")
            details.append({"minute": _text(clock.get("displayValue") or event.get("displayClock")),
                            "description": description[:350], "team": _text(team.get("displayName")),
                            "kind": kind})
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
    officials = []
    for official in _list(game_info.get("officials"))[:8]:
        official = _dict(official)
        name = _text(official.get("displayName") or official.get("fullName"))
        if name:
            officials.append({"name": name, "role": _text(official.get("position") or official.get("type"))})
    weather = _dict(game_info.get("weather"))
    roster_groups = _list(payload.get("rosters"))
    lineups = []
    for group in roster_groups[:2]:
        group = _dict(group)
        club = _dict(group.get("team"))
        players = []
        for member in _list(group.get("roster"))[:30]:
            member = _dict(member)
            athlete = _dict(member.get("athlete")) or member
            name = _text(athlete.get("displayName") or athlete.get("fullName"))
            if name:
                players.append({"name": name, "starter": bool(member.get("starter", False)),
                                "number": _text(athlete.get("jersey")),
                                "position": _text(_dict(athlete.get("position")).get("abbreviation"))})
        if players:
            lineups.append({"team": _text(club.get("displayName")), "players": players})
    return {"venue": _text(venue.get("fullName")), "attendance": _int(game_info.get("attendance")),
            "events": details, "teams": teams, "officials": officials,
            "weather": _text(weather.get("displayValue") or weather.get("description")),
            "lineups": lineups, "source": "ESPN"}


def normalize_club(payload: dict, league: str) -> dict:
    """Read optional team identity and venue/year only when ESPN supplies them."""
    base = _dict(payload)
    team = _dict(base.get("team")) or base
    logos = _list(team.get("logos"))
    location = _text(team.get("location"))
    venue = _dict(team.get("venue")) or _dict(base.get("venue"))
    stadium = _text(venue.get("fullName") or venue.get("displayName") or
                    team.get("stadium") or base.get("stadium"))
    founded = team.get("founded") or team.get("foundedYear") or team.get("yearFounded") or team.get("established")
    if isinstance(founded, dict):
        founded = founded.get("year")
    founded_year = _text(founded)
    if not (founded_year.isascii() and founded_year.isdigit() and 1800 <= int(founded_year) <= 2100):
        founded_year = ""
    return {
        "id": _text(team.get("id")), "league": league,
        "name": _text(team.get("displayName") or team.get("name")),
        "abbreviation": _text(team.get("abbreviation")),
        "location": location,
        "stadium": stadium[:150], "founded_year": founded_year,
        "logo": _url(_dict(logos[0]).get("href") if logos else team.get("logo")),
        "color": _text(team.get("color"))[:6],
        "links": [{"label": _text(_dict(link).get("text")), "url": _url(_dict(link).get("href"))}
                  for link in _list(team.get("links"))[:8] if _url(_dict(link).get("href"))],
    }


def normalize_roster(payload: dict) -> list[dict]:
    """A safe subset of available squad and athlete information."""
    source = _dict(payload)
    athletes = _list(source.get("athletes"))
    if not athletes:
        for group in _list(source.get("groups")):
            athletes.extend(_list(_dict(group).get("athletes")))
    output = []
    for item in athletes[:80]:
        athlete = _dict(item)
        if not athlete.get("displayName"):
            continue
        position = _dict(athlete.get("position"))
        output.append({
            "id": _text(athlete.get("id")), "name": _text(athlete.get("displayName")),
            "position": _text(position.get("displayName") or position.get("abbreviation")),
            "number": _text(athlete.get("jersey")), "photo": espn_athlete_photo(athlete),
            "age": _int(athlete.get("age")),
        })
    return output


def normalize_leaders(payload: dict) -> list[dict]:
    """Normalize *labelled* season-wide ESPN leader data.

    Expects ESPN to provide ranked categories, not a small match sample.
    Never infer leaderboards from individual results or unrelated stats.
    """
    from math import isfinite

    categories = {
        "goals": ("goals", "goal", "g", "gl", "goalsscored", "totalgoals",
                  "scoringgoals", "goalscorers", "topscorers", "goalscoring"),
        "assists": ("assists", "assist", "ast", "totalassists", "topassists"),
        "yellow_cards": ("yellowcards", "yellowcard", "yellow", "yc", "yellowcardsshown"),
        "red_cards": ("redcards", "redcard", "red", "rc", "redcardsshown"),
        "rating": ("rating", "ratings", "playerrating", "averagerating", "avgrating"),
        "appearances": ("appearances", "appearance", "gamesplayed", "matchesplayed", "apps", "gp"),
        "minutes": ("minutesplayed", "minutes", "mins", "minplayed", "playingtime"),
    }
    aliases = {alias: key for key, values in categories.items() for alias in values}

    def kind(name):
        cleaned = "".join(c for c in str(name or "").casefold() if c.isalnum())
        return aliases.get(cleaned, "")

    def unwrap(value):
        if isinstance(value, dict):
            value = value.get("value", value.get("displayValue"))
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        try:
            return float(value) if value is not None and not isinstance(value, bool) else None
        except (ValueError, TypeError, OverflowError):
            return None

    result = {}

    def add(athlete, team, label, value):
        category = kind(label)
        if not category:
            return
        athlete, team = _dict(athlete), _dict(team)
        player = _text(athlete.get("displayName") or athlete.get("fullName") or athlete.get("name"))
        number = unwrap(value)
        if not player or number is None or not isfinite(number) or number <= 0:
            return
        # All stats except rating must represent whole counts.
        if category != "rating" and not number.is_integer():
            return
        if category == "rating" and not (0 < number <= 10):
            return
        value = round(number, 2) if category == "rating" else int(number)
        ident = _text(athlete.get("id")) or player.casefold()
        key = (category, ident)
        team = team or _dict(athlete.get("team"))
        photo = espn_athlete_photo(athlete)
        row = {"category": category, "player": player[:100],
               "team": _text(team.get("displayName") or team.get("name"))[:100],
               "value": value, "photo": photo, "player_id": _text(athlete.get("id")),
               "source": "ESPN"}
        old = result.get(key)
        if not old or number > old["value"] or (number == old["value"] and (not old["team"] and row["team"])):
            result[key] = row

    def items(value):
        return value if isinstance(value, list) else []

    source = _dict(payload)
    groups = (items(source.get("leaders")) + items(source.get("categories")) +
              items(source.get("statistics")) + items(source.get("items")) +
              items(_dict(source.get("data")).get("categories")))
    # Ranked ESPN Core leader groups: categories[].leaders[].athlete.
    for group in groups[:80]:
        group = _dict(group)
        cat = group.get("name") or group.get("displayName") or group.get("abbreviation")
        for leader in (items(group.get("leaders")) + items(group.get("entries")) +
                       items(group.get("athletes")))[:50]:
            leader = _dict(leader)
            label = _text(leader.get("statName") or cat)
            add(leader.get("athlete") or leader.get("player") or leader,
                leader.get("team"), label,
                leader.get("value", leader.get("displayValue")))

    # ESPN Web API by-athlete ranked outputs sometimes store stats under
    # labels and parallel values; those arrays have to line up exactly.
    wrappers = (items(source.get("athletes")) + items(source.get("entries")) +
                items(_dict(source.get("data")).get("athletes")) +
                items(_dict(source.get("data")).get("entries")))
    for wrapper in wrappers[:120]:
        w = _dict(wrapper)
        athlete = _dict(w.get("athlete")) or _dict(w.get("player")) or w
        team = _dict(w.get("team")) or _dict(athlete.get("team"))
        for field in ("stats", "statistics", "totals"):
            obj = w.get(field)
            if isinstance(obj, dict):
                for label, value in obj.items():
                    add(athlete, team, label, value)
            elif isinstance(obj, list):
                for stat in obj[:80]:
                    stat = _dict(stat)
                    label = stat.get("name") or stat.get("displayName") or stat.get("abbreviation")
                    add(athlete, team, label, stat.get("value", stat.get("displayValue")))
        def nested_stats(value, parent="", depth=0):
            if depth > 6:
                return
            if isinstance(value, list):
                for record in value[:100]:
                    nested_stats(record, parent, depth + 1)
            elif isinstance(value, dict):
                label = value.get("name") or value.get("displayName") or value.get("abbreviation") or parent
                if "value" in value or "displayValue" in value:
                    add(athlete, team, label, value.get("value", value.get("displayValue")))
                labels = items(value.get("names")) or items(value.get("labels"))
                values = items(value.get("totals")) or items(value.get("values"))
                for label_name, amount in zip(labels[:80], values[:80]):
                    add(athlete, team, label_name, amount)
                for field in ("splits", "categories", "stats", "statistics", "totals", "groups"):
                    child = value.get(field)
                    if isinstance(child, dict):
                        for child_name, part in list(child.items())[:80]:
                            nested_stats(part, child_name, depth + 1)
                    elif isinstance(child, list):
                        nested_stats(child, label, depth + 1)
        for field in ("splits", "categories", "stats", "statistics"):
            nested_stats(w.get(field))

    order = {"goals": 0, "assists": 1, "yellow_cards": 2, "red_cards": 3,
             "rating": 4, "appearances": 5, "minutes": 6}
    return sorted(result.values(), key=lambda row: (order.get(row["category"], 99), -row["value"], row["player"]))[:180]
