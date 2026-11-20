"""Next competition round from cached fixtures, suitable for Assist/TTS.

No network I/O, persistence, or work in Home Assistant startup. ESPN sometimes
provides a numbered matchday; if it does not, use a clearly labelled, bounded
week-like group instead of inventing an official round number.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_MATCHES_ATTRIBUTE_BYTES = 7800
MAX_VOICE_TEXT_BYTES = 4600
MAX_VOICE_MATCHES = 30


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo is not None else None


def _round_number(value: object) -> int | None:
    # Python bool is an int but is not a valid ESPN matchday.
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if 1 <= number <= 100 and str(value).strip() == str(number) else None


def schedule_next_round(
    fixtures: list[dict], league_code: str, league_name: str,
    time_zone: str = "UTC", now: datetime | None = None,
) -> dict:
    """Return every known fixture in the next playable round of one league.

    The round containing the earliest pending/live fixture is selected. Include
    the other games in that same matchday even if some already finished; do not
    mix fixtures from other numbered rounds. Where ESPN omits round numbers,
    estimate one near-term slate (not a fictional official round).
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must have timezone")
    now = now.astimezone(timezone.utc)
    try:
        tz = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        tz = timezone.utc
        time_zone = "UTC"

    rows = []
    seen = set()
    for item in fixtures or []:
        if not isinstance(item, dict) or item.get("state") not in ("pre", "in", "post"):
            continue
        if item.get("league") and item["league"] != league_code:
            continue
        kickoff = _date(item.get("kickoff"))
        if kickoff is None:
            continue
        home = item.get("home") if isinstance(item.get("home"), dict) else {}
        away = item.get("away") if isinstance(item.get("away"), dict) else {}
        identity = str(item.get("id") or "") or f"{kickoff.isoformat()}|{home.get('id', home.get('name'))}|{away.get('id', away.get('name'))}"
        if identity in seen:
            continue
        seen.add(identity)
        rows.append((kickoff, identity, _round_number(item.get("round")), item, home, away))
    rows.sort(key=lambda row: (row[0], row[1]))

    # Keep live events in the active slate; never treat a week-old stale PRE as
    # a future fixture or return a completed round with nothing left to play.
    pending = [row for row in rows if
               (row[3]["state"] == "pre" and row[0] >= now - timedelta(minutes=5)) or
               (row[3]["state"] == "in" and row[0] >= now - timedelta(hours=6))]
    anchor = min(pending, key=lambda row: (row[0] if row[0] >= now else now, row[1])) if pending else None
    round_number = anchor[2] if anchor else None
    round_source = "espn" if round_number is not None else "estimated" if anchor else "none"

    if anchor is None:
        selected = []
        round_label = "Chưa có vòng tiếp theo"
    elif round_number is not None:
        # Numbered matchdays are an authoritative grouping, but do not join a
        # previous season's same numbered round if a stale feed spans seasons.
        selected = [row for row in rows if row[2] == round_number and
                    abs((row[0] - anchor[0]).days) <= 21]
        round_label = f"Vòng {round_number}"
    else:
        # Fallback: a labelled rolling slate, not an asserted official round.
        # One encounter per club, so a midweek match cannot pull in a second
        # game for the same team later in the next week's fixtures.
        window_start = anchor[0] - timedelta(days=3)
        window_end = anchor[0] + timedelta(days=7)
        selected = []
        used_teams = set()
        for row in rows:
            if row[2] is not None or not (window_start <= row[0] < window_end):
                continue
            ids = {str(team.get("id") or team.get("name") or "").strip().casefold()
                   for team in (row[4], row[5])}
            ids.discard("")
            if used_teams & ids:
                continue
            selected.append(row)
            used_teams.update(ids)
        round_label = "Đợt thi đấu sắp tới (ước tính)"

    matches = []
    for kickoff, identity, _num, item, home, away in selected:
        local = kickoff.astimezone(tz)
        matches.append({
            "id": str(item.get("id") or ""),
            "kickoff": kickoff.isoformat(),
            "local_time": local.strftime("%d/%m %H:%M"),
            "home": str(home.get("name") or "Chưa xác định")[:90],
            "away": str(away.get("name") or "Chưa xác định")[:90],
            "state": item["state"],
        })

    listed = []
    for match in matches:
        trial = listed + [match]
        if len(json.dumps(trial, ensure_ascii=True).encode("utf-8")) > MAX_MATCHES_ATTRIBUTE_BYTES:
            break
        listed.append(match)

    if not matches:
        voice_text = f"Giải {league_name} chưa có dữ liệu về vòng đấu tiếp theo."
    else:
        speech = [f"{round_label} của giải {league_name}, gồm {len(matches)} cặp đấu."]
        spoken = 0
        for match in matches[:MAX_VOICE_MATCHES]:
            local = _date(match["kickoff"]).astimezone(tz)
            sentence = (
                f"Ngày {local.day} tháng {local.month}, lúc {local.hour} giờ "
                f"{local.minute:02d}: {match['home']} gặp {match['away']}."
            )
            if len(json.dumps(" ".join(speech + [sentence]), ensure_ascii=True).encode("utf-8")) > MAX_VOICE_TEXT_BYTES - 130:
                break
            speech.append(sentence)
            spoken += 1
        if len(matches) > spoken:
            speech.append(f"Còn {len(matches) - spoken} trận nữa trong vòng này.")
        voice_text = " ".join(speech)

    return {
        "league": league_name,
        "league_code": league_code,
        "round_number": round_number,
        "round_label": round_label,
        "round_source": round_source,
        "time_zone": time_zone,
        "total_matches": len(matches),
        "upcoming_matches": sum(row[3]["state"] in ("pre", "in") for row in selected),
        "listed_matches": len(listed),
        "truncated": len(listed) < len(matches),
        "matches": listed,
        "voice_text": voice_text,
    }
