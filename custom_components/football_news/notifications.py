"""Opt-in Zalo Bot messages, using the user's existing Zalo Bot integration.

Zalo rich text syntax and thread protection match the supplied Zalo README.
No Zalo credentials are stored here; service calls stay within Home Assistant.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, DEFAULT_OPTIONS
from .live_events import extract_events

_LOGGER = logging.getLogger(__name__)


def _safe(text: Any, limit: int = 110) -> str:
    """Avoid user/provider-supplied rich-text tokens in formatted notifications."""
    result = str(text or "").replace("{", "(").replace("}", ")").replace("*", "").replace("\n", " ")
    return result.strip()[:limit]


def _time(iso: str, tz) -> str:
    try:
        parsed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(tz).strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return "Chưa xác định"



def _goal_clock_key(text: str) -> tuple[int, int]:
    """Compare match minutes, including stoppage time (45+2, 90+4)."""
    match = re.search(r"(\d{1,3})(?:\s*\+\s*(\d{1,2}))?", str(text or ""))
    if not match:
        return (-1, -1)
    return int(match.group(1)), int(match.group(2) or 0)


def _confirmed_summary_score(summary: dict) -> tuple[int, int] | None:
    """Read ESPN summary's explicit home/away scoreboard, never guess it."""
    if not isinstance(summary, dict):
        return None
    header = summary.get("header")
    competitions = header.get("competitions") if isinstance(header, dict) else None
    if not isinstance(competitions, list) or not competitions:
        return None
    competitors = competitions[0].get("competitors") if isinstance(competitions[0], dict) else None
    if not isinstance(competitors, list):
        return None
    scores = {}
    for item in competitors:
        if not isinstance(item, dict) or item.get("homeAway") not in {"home", "away"}:
            continue
        value = item.get("score")
        if isinstance(value, dict):
            value = value.get("value", value.get("displayValue"))
        if type(value) is int:
            parsed = value
        elif isinstance(value, str) and value.isascii() and value.isdecimal():
            parsed = int(value)
        else:
            continue
        if 0 <= parsed <= 99:
            scores[item["homeAway"]] = parsed
    if len(scores) != 2:
        return None
    return scores["home"], scores["away"]


def goal_details_from_summary(match: dict, previous_scores: list, summary: dict) -> list[dict]:
    """Attribute a new *verified* score increment to ESPN timeline goal(s).

    Goals and scores are different ESPN feeds. Require a matching summary
    scoreboard and a complete goal sequence for the affected team; otherwise
    reporting an older scorer as the new goal would be misleading. Own goals,
    missing timeline entries and provisional VAR adjustments safely fall back
    to score-only notifications.
    """
    if not isinstance(previous_scores, list) or len(previous_scores) != 2:
        return []
    before = previous_scores
    after = [match.get(side, {}).get("score") for side in ("home", "away")]
    if not all(type(n) is int and n >= 0 for n in before + after):
        return []
    if any(new < old for old, new in zip(before, after, strict=True)):
        return []
    if _confirmed_summary_score(summary) != tuple(after):
        return []
    timeline = extract_events(summary, match)
    if timeline is None:
        return []
    changes = []
    for index, side in enumerate(("home", "away")):
        old_score, new_score = before[index], after[index]
        if new_score <= old_score:
            continue
        team = match.get(side, {})
        team_name = str(team.get("name") or "").strip()
        if not team_name:
            return []
        goals = [event for event in timeline if event["type"] == "goal"
                 and event.get("team", "").casefold() == team_name.casefold()]
        # The ESPN timeline must account for *all* of this team's goals.
        # Otherwise we cannot tell if its most recent entry is the new goal.
        if len(goals) != new_score:
            return []
        goals.sort(key=lambda event: _goal_clock_key(event.get("minute", "")))
        for event in goals[old_score:new_score]:
            changes.append({
                "team": team_name,
                "player": event.get("player", ""),
                "minute": event.get("minute", ""),
            })
    changes.sort(key=lambda event: _goal_clock_key(event["minute"]))
    return changes


def build_message(kind: str, item: dict, league_name: str, tz, *, goal_details: list[dict] | None = None) -> str:
    """Rich-text messages using supported Zalo tags (no arbitrary HEX colors)."""
    league = _safe(league_name)
    if kind == "news":
        return ("{big}{green}**📰 FOOTBALL NEWS · TIN MỚI**{/green}{/big}\n"
                f"{_safe(item.get('title'), 240)}\n"
                f"🏆 {league}\n"
                f"🔗 {item.get('url', '')}\n"
                "{small}Nguồn: ESPN · Thông báo từ Home Assistant{/small}")
    home = _safe(item.get("home", {}).get("name"))
    away = _safe(item.get("away", {}).get("name"))
    match = f"**{home}**  ⚔️  **{away}**"
    if kind == "schedule":
        return ("{big}{orange}**⏰ FOOTBALL NEWS · SẮP THI ĐẤU**{/orange}{/big}\n"
                f"{match}\n🏆 {league}\n🗓 {_time(item.get('kickoff', ''), tz)}\n"
                f"🏟 {_safe(item.get('venue') or 'Đang cập nhật')}\n"
                "{small}Lịch có thể thay đổi · Giờ theo múi giờ Home Assistant{/small}")
    if kind == "goal":
        h = item.get("home", {}).get("score")
        a = item.get("away", {}).get("score")
        if type(h) is not int or type(a) is not int:
            raise ValueError("Cannot announce a goal without a verified score")
        details = goal_details or []
        if details:
            incidents = "\n".join(
                f"⚽ {_safe(goal.get('team') or 'Đội ghi bàn')}"
                f"\n👤 Cầu thủ: {_safe(goal.get('player') or 'ESPN đang cập nhật')}"
                f"\n⏱ Phút: {_safe(goal.get('minute') or 'ESPN đang cập nhật')}"
                for goal in details[:6]
            )
            return ("{big}{orange}**⚽ FOOTBALL NEWS · BÀN THẮNG**{/orange}{/big}\n"
                    f"{match}\n{{big}}**{h} - {a}**{{/big}}\n"
                    f"{incidents}\n🏆 {league}\n"
                    "{small}Cầu thủ và phút từ diễn biến ESPN{/small}")
        return ("{big}{orange}**⚽ FOOTBALL NEWS · BÀN THẮNG / CẬP NHẬT TỶ SỐ**{/orange}{/big}\n"
                f"{match}\n{{big}}**{h} - {a}**{{/big}}\n🏆 {league}\n"
                "{small}ESPN chưa xác nhận cầu thủ/phút ghi bàn; có thể là điều chỉnh tỷ số{/small}")
    if kind == "kickoff":
        return ("{big}{green}**⚽ FOOTBALL NEWS · BẮT ĐẦU**{/green}{/big}\n"
                f"{match}\n🏆 {league}\n🕒 {_time(item.get('kickoff', ''), tz)}\n"
                "{small}Dữ liệu trận đấu: ESPN{/small}")
    score_h = item.get("home", {}).get("score")
    score_a = item.get("away", {}).get("score")
    if score_h is None or score_a is None:
        raise ValueError("Cannot send result without verified scores")
    return ("{big}{green}**🏁 FOOTBALL NEWS · KẾT QUẢ**{/green}{/big}\n"
            f"{match}\n"
            f"{{big}}**{score_h} - {score_a}**{{/big}}\n"
            f"🏆 {league}\n🗓 {_time(item.get('kickoff', ''), tz)}\n"
            "{small}Kết quả theo dữ liệu ESPN · Home Assistant{/small}")


class ZaloNotifier:
    """Deduplicate status transitions and delayed schedule reminders."""

    def __init__(self, hass: HomeAssistant, entry, league_name: str, provider=None) -> None:
        self.hass = hass
        self.entry = entry
        self.league_name = league_name
        self.provider = provider
        self._store = Store(hass, 1, f"{DOMAIN}_alerts_{entry.entry_id}")
        self._lock = asyncio.Lock()
        self._loaded = False
        self._seen: dict[str, Any] = {"fixtures": {}, "news": [], "reminders": [], "scores": {}}

    async def _load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            for key in self._seen:
                if isinstance(saved.get(key), type(self._seen[key])):
                    self._seen[key] = saved[key]
        self._loaded = True

    def _save(self) -> None:
        snapshot = {
            "fixtures": dict(list(self._seen["fixtures"].items())[-600:]),
            "news": self._seen["news"][:200],
            "reminders": self._seen["reminders"][-600:],
            "scores": dict(list(self._seen["scores"].items())[-600:]),
        }
        self._seen = snapshot
        self._store.async_delay_save(lambda: snapshot, 30)

    def _settings(self) -> dict:
        return {**DEFAULT_OPTIONS, **self.entry.options}

    async def send(self, message: str) -> bool:
        options = self._settings()
        if not options.get("zalo_enabled"):
            return False
        account = str(options.get("zalo_account") or "").strip()
        thread_id = str(options.get("zalo_thread_id") or "").strip()
        type_id = str(options.get("zalo_thread_type") or "1")
        if not account or not thread_id or type_id not in {"0", "1"}:
            _LOGGER.warning("Zalo notification not sent: incomplete notification options")
            return False
        if not self.hass.services.has_service("zalo_bot", "send_message"):
            _LOGGER.warning("Zalo notification not sent: zalo_bot.send_message unavailable")
            return False
        if not thread_id.startswith("zalo:"):
            thread_id = "zalo:" + thread_id
        try:
            await self.hass.services.async_call(
                "zalo_bot", "send_message",
                {"account_selection": account, "thread_id": thread_id,
                 "type": type_id, "message": message},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.warning("Zalo delivery failed (%s); message and IDs omitted", type(err).__name__)
            return False
        _LOGGER.debug("Zalo message delivered successfully; sensitive fields omitted")
        return True

    async def process(self, data: dict) -> None:
        """Called after refresh; never holds startup or coordinator data fetch."""
        async with self._lock:
            await self._load()
            opts = self._settings()
            fixtures = data.get("fixtures", [])
            articles = data.get("news", [])
            previous = self._seen["fixtures"]
            before = self._seen["news"]
            old_scores = self._seen["scores"]
            first_run = not previous and not before
            now = datetime.now(timezone.utc)
            tz = self.hass.config.time_zone
            if isinstance(tz, str):
                from zoneinfo import ZoneInfo
                try:
                    tz = ZoneInfo(tz)
                except KeyError:
                    tz = timezone.utc
            current = {str(x["id"]): x.get("state", "pre") for x in fixtures}
            team_ids = {str(team_id) for team_id in opts.get("zalo_team_ids", []) if str(team_id).strip()}
            team_names = [str(name).casefold().strip() for name in opts.get("zalo_team_names", []) if str(name).strip()]
            legacy_filter = str(opts.get("team_filter") or "").casefold().strip() if not team_ids else ""
            manager = getattr(self.hass, "data", {}).get(DOMAIN, {}).get("preferences")
            preferences = await manager.read() if manager is not None else {}
            selected_matches = preferences.get("matches", [])
            selected_for_league = {item.split(":", 1)[-1] for item in selected_matches
                                   if item.startswith(self.entry.data["league"] + ":")}
            def relevant(match: dict) -> bool:
                if selected_for_league and str(match.get("id")) not in selected_for_league:
                    return False
                if team_ids:
                    return any(str(match.get(side, {}).get("id", "")) in team_ids for side in ("home", "away"))
                return not legacy_filter or any(legacy_filter in str(match.get(side, {}).get("name", "")).casefold()
                                               for side in ("home", "away"))

            if opts.get("zalo_enabled"):
                for match in fixtures:
                    if not relevant(match):
                        continue
                    match_id = str(match["id"])
                    before_state = previous.get(match_id)
                    state = match.get("state")
                    if before_state == "pre" and state == "in" and opts.get("kickoff_alerts"):
                        await self.send(build_message("kickoff", match, self.league_name, tz))
                    home_score = match.get("home", {}).get("score")
                    away_score = match.get("away", {}).get("score")
                    current_score = [home_score, away_score]
                    previous_score = old_scores.get(match_id)
                    if (opts.get("goal_alerts") and state == "in" and before_state == "in"
                            and isinstance(previous_score, list) and len(previous_score) == 2
                            and all(type(x) is int for x in previous_score + current_score)
                            and any(new > old for old, new in zip(previous_score, current_score, strict=True))):
                        details = []
                        if self.provider is not None:
                            try:
                                # Zalo work is already scheduled off the HA
                                # coordinator refresh. One bounded provider
                                # lookup uses the shared 12-second summary cache.
                                summary = await asyncio.wait_for(
                                    self.provider.summary(match_id), timeout=5.0)
                                details = goal_details_from_summary(match, previous_score, summary)
                            except Exception as err:
                                _LOGGER.debug("Zalo goal attribution unavailable league=%s match=%s cause=%s",
                                              getattr(self.entry, "data", {}).get("league", "?"), match_id,
                                              type(err).__name__)
                        if not details:
                            _LOGGER.debug("Zalo sending score-only update match=%s: ESPN attribution unverified",
                                          match_id)
                        await self.send(build_message("goal", match, self.league_name, tz,
                                                      goal_details=details))
                    if before_state in {"pre", "in"} and state == "post" and opts.get("result_alerts"):
                        if match.get("home", {}).get("score") is not None and match.get("away", {}).get("score") is not None:
                            await self.send(build_message("result", match, self.league_name, tz))
                    if state == "pre" and opts.get("schedule_alerts"):
                        try:
                            kick = datetime.fromisoformat(match.get("kickoff", "").replace("Z", "+00:00"))
                            minutes_until = (kick - now).total_seconds() / 60
                        except (ValueError, TypeError):
                            continue
                        reminder = int(opts.get("reminder_minutes", 30))
                        reminder_key = f"{match_id}:{reminder}:{match.get('kickoff')}"
                        if 0 <= minutes_until <= reminder and reminder_key not in self._seen["reminders"]:
                            if await self.send(build_message("schedule", match, self.league_name, tz)):
                                self._seen["reminders"].append(reminder_key)
                if opts.get("news_alerts") and not first_run:
                    for article in reversed(articles[:5]):
                        if article["id"] in before:
                            continue
                        if team_ids or legacy_filter:
                            # Do not send league-wide news to subscribers of
                            # specific clubs. A known team name must occur.
                            haystack = (str(article.get("title", "")) + " " +
                                        str(article.get("description", ""))).casefold()
                            allowed_names = team_names or ([legacy_filter] if legacy_filter else [])
                            if not allowed_names or not any(name in haystack for name in allowed_names):
                                continue
                        # Do not send old items that resurfaced in the provider feed.
                        try:
                            published = datetime.fromisoformat(article.get("published", "").replace("Z", "+00:00"))
                            if published.tzinfo is None:
                                published = published.replace(tzinfo=timezone.utc)
                            if abs((now - published).total_seconds()) > 3 * 3600:
                                continue
                        except (TypeError, ValueError):
                            continue
                        await self.send(build_message("news", article, self.league_name, tz))
            self._seen["fixtures"] = {**previous, **current}
            self._seen["scores"] = {
                **old_scores,
                **{str(m["id"]): [m.get("home", {}).get("score"), m.get("away", {}).get("score")]
                   for m in fixtures},
            }
            self._seen["news"] = list(dict.fromkeys([x["id"] for x in articles] + before))[:200]
            self._save()
