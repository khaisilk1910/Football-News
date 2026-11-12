"""Football News - independent, privacy-aware Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import voluptuous as vol
import probatio
from homeassistant.components import websocket_api
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .const import DOMAIN, VERSION, LEAGUES, STARTER_LEAGUES
from .coordinator import FootballNewsCoordinator
from .notifications import ZaloNotifier
from .provider import FootballProvider, ProviderError
from .models import normalize_summary
from .preferences import FootballPreferences
from .snapshot import competition_snapshot, runtime_for_entry

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ("sensor", "binary_sensor")
_ROOT = Path(__file__).parent


def _runtime(hass: HomeAssistant, entry_id: str = ""):
    runtimes = hass.data.get(DOMAIN, {}).get("entries", {})
    if entry_id and entry_id in runtimes:
        return runtimes[entry_id]
    for entry in hass.config_entries.async_entries(DOMAIN):
        if not entry_id or entry.entry_id == entry_id:
            runtime = runtime_for_entry(entry, runtimes)
            if runtime:
                return runtime
    return None


def _league_runtime(hass: HomeAssistant, league: str):
    runtimes = hass.data.get(DOMAIN, {}).get("entries", {})
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("league") == league:
            return runtime_for_entry(entry, runtimes)
    return None


@websocket_api.websocket_command({"type": "football_news/data", probatio.Optional("entry_id"): str})
@websocket_api.async_response
async def ws_get_data(hass: HomeAssistant, connection, msg):
    """Authenticated frontend snapshot, without leaking Zalo destination IDs."""
    # Settings can already contain six leagues while their async_setup_entry
    # is loading/retrying. The config-entry registry, not hass.data runtimes,
    # is the source of truth for the configured count.
    configured = list(hass.config_entries.async_entries(DOMAIN))
    runtimes = hass.data.get(DOMAIN, {}).get("entries", {})
    if not configured and runtimes:
        # A transient HA config-entry registry rehydration must not hide loaded
        # competitions. Runtime entries are already owned by this integration.
        configured = [runtime["entry"] for runtime in runtimes.values()
                      if isinstance(runtime, dict) and runtime.get("entry") is not None]
    leagues = competition_snapshot(configured, runtimes, LEAGUES)
    runtime = _runtime(hass, msg.get("entry_id", ""))
    if not runtime and configured:
        runtime = next((runtime_for_entry(entry, runtimes) for entry in configured
                        if runtime_for_entry(entry, runtimes)), None)
    coordinator = runtime["coordinator"] if runtime else None
    current = (coordinator.data if coordinator else None) or {}
    data = {"fixtures": current.get("fixtures", []),
            "standings": current.get("standings", []),
            "news": current.get("news", []),
            "updated_at": current.get("updated_at", {}),
            "errors": current.get("errors", [])}
    preferences = await hass.data[DOMAIN]["preferences"].read()
    lang_entry = runtime["entry"] if runtime else (configured[0] if configured else None)
    connection.send_result(msg["id"], {
        **data,
        "league": LEAGUES.get(coordinator.provider.league, coordinator.provider.league) if coordinator else "",
        "entry_id": runtime["entry"].entry_id if runtime else "",
        "language": lang_entry.options.get("locale", "vi") if lang_entry else "vi",
        "leagues": leagues,
        "preferences": preferences,
        "starter_leagues": [{"code": code, "name": LEAGUES[code]} for code in STARTER_LEAGUES],
        "configured_count": len(leagues),
        "runtime_count": sum(1 for row in leagues if row["runtime_loaded"]),
        "admin": bool(connection.user and connection.user.is_admin),
    })


@websocket_api.websocket_command({
    "type": "football_news/quick_setup",
    probatio.Optional("leagues"): [str],
})
@websocket_api.async_response
async def ws_quick_setup(hass: HomeAssistant, connection, msg):
    """Explicit administrator action to add multiple ESPN league entries.

    Uses regular HA config flows so each league has a native config entry,
    sensor entities and independent error state. Never run this at startup.
    """
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    requested = list(dict.fromkeys(msg.get("leagues") or STARTER_LEAGUES))
    if not requested or len(requested) > 8 or any(code not in LEAGUES for code in requested):
        connection.send_error(msg["id"], "invalid", "Choose one to eight known competitions")
        return
    configured = {e.data.get("league") for e in hass.config_entries.async_entries(DOMAIN)}
    added, failures = [], []
    for code in requested:
        if code in configured:
            continue
        try:
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}, data={"league": code})
            result_type = getattr(result["type"], "value", result["type"])
            if result_type == "create_entry":
                configured.add(code)
                added.append(code)
            else:
                failures.append(f"{code}: {result_type}")
        except Exception as exc:
            _LOGGER.exception("Football News quick setup failed for %s", code)
            failures.append(f"{code}: {type(exc).__name__}")
    _LOGGER.info("Football News quick setup: %d added, %d skipped, %d errors",
                 len(added), len(requested) - len(added) - len(failures), len(failures))
    connection.send_result(msg["id"], {"added": added, "errors": failures,
                                        "configured": len(configured)})


@websocket_api.websocket_command({"type": "football_news/reload_entries"})
@websocket_api.async_response
async def ws_reload_entries(hass: HomeAssistant, connection, msg):
    """Explicit repair action for configured-but-unloaded competitions."""
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    entries = list(hass.config_entries.async_entries(DOMAIN))
    results = await asyncio.gather(
        *(hass.config_entries.async_reload(entry.entry_id) for entry in entries),
        return_exceptions=True,
    )
    errors = [f"{entry.data.get('league', entry.entry_id)}: {type(result).__name__}"
              for entry, result in zip(entries, results, strict=True)
              if isinstance(result, Exception) or result is False]
    _LOGGER.info("Football News reload requested: entries=%d failures=%d", len(entries), len(errors))
    connection.send_result(msg["id"], {"entries": len(entries), "errors": errors})


@websocket_api.websocket_command({
    "type": "football_news/teams", probatio.Required("league"): str,
})
@websocket_api.async_response
async def ws_teams(hass: HomeAssistant, connection, msg):
    """Get the team directory only when a viewer opens My Clubs."""
    runtime = _league_runtime(hass, msg["league"])
    if not runtime:
        connection.send_error(msg["id"], "not_found", "Competition is not configured")
        return
    try:
        teams = await runtime["coordinator"].provider.teams()
    except ProviderError as err:
        _LOGGER.warning("Team list unavailable for %s: %s", msg["league"], err)
        connection.send_error(msg["id"], "provider_error", str(err)[:180])
        return
    connection.send_result(msg["id"], {"league": msg["league"], "teams": teams})


@websocket_api.websocket_command({"type": "football_news/match", probatio.Required("event_id"): str, probatio.Optional("entry_id"): str, probatio.Optional("league"): str})
@websocket_api.async_response
async def ws_match(hass: HomeAssistant, connection, msg):
    """Fetch optional match statistics only when a viewer requests them."""
    runtime = _runtime(hass, msg.get("entry_id", ""))
    code = msg.get("league")
    if code:
        runtime = _league_runtime(hass, code)
    if not runtime:
        connection.send_error(msg["id"], "not_found", "Football News league not configured")
        return
    try:
        payload = await runtime["coordinator"].provider.summary(msg["event_id"])
    except ProviderError as err:
        _LOGGER.warning("On-demand match detail unavailable (%s)", type(err).__name__)
        connection.send_error(msg["id"], "provider_error", "Match details are unavailable")
        return
    connection.send_result(msg["id"], normalize_summary(payload))


@websocket_api.websocket_command({"type": "football_news/fixtures_month", probatio.Required("month"): str, probatio.Required("league"): str})
@websocket_api.async_response
async def ws_fixtures_month(hass: HomeAssistant, connection, msg):
    """On-demand monthly calendar, optionally across up to eight leagues.

    A failed league does not hide valid fixtures from another, and an empty
    successful month is different from a network failure.
    """
    month, selected = msg["month"], msg["league"]
    from datetime import datetime
    try:
        datetime.strptime(month, "%Y-%m")
        if len(month) != 7:
            raise ValueError("invalid length")
    except ValueError:
        connection.send_error(msg["id"], "invalid", "Month must be YYYY-MM")
        return
    if selected == "all":
        configured = list(hass.config_entries.async_entries(DOMAIN))
        if len(configured) > 8:
            connection.send_error(msg["id"], "too_many_leagues", "Select a competition to load this month")
            return
        runtimes = [runtime_for_entry(entry, hass.data.get(DOMAIN, {}).get("entries", {}))
                    for entry in configured]
        runtimes = [runtime for runtime in runtimes if runtime]
    else:
        runtime = _league_runtime(hass, selected)
        runtimes = [runtime] if runtime else []
    if not runtimes:
        connection.send_error(msg["id"], "not_found", "No active competition is configured")
        return
    results = await asyncio.gather(
        *(runtime["coordinator"].provider.fixtures_month(month) for runtime in runtimes),
        return_exceptions=True,
    )
    fixtures, errors = [], []
    for runtime, result in zip(runtimes, results, strict=True):
        league = runtime["coordinator"].provider.league
        if isinstance(result, Exception):
            _LOGGER.warning("Monthly fixtures failed: league=%s month=%s reason=%s", league, month, result)
            errors.append(f"{LEAGUES.get(league, league)}: {type(result).__name__}")
        else:
            fixtures.extend({**fixture, "league": league,
                             "league_name": LEAGUES.get(league, league)} for fixture in result)
    if errors and len(errors) == len(runtimes):
        connection.send_error(msg["id"], "provider_error", "No calendar data: " + "; ".join(errors)[:180])
        return
    fixtures.sort(key=lambda fixture: fixture.get("kickoff") or "")
    connection.send_result(msg["id"], {"league": selected, "month": month,
                                        "fixtures": fixtures[:800], "errors": errors})


@websocket_api.websocket_command({"type": "football_news/club", probatio.Required("team_id"): str, probatio.Required("league"): str})
@websocket_api.async_response
async def ws_club(hass: HomeAssistant, connection, msg):
    runtime = _league_runtime(hass, msg["league"])
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    provider = runtime["coordinator"].provider
    try:
        club = await provider.club(msg["team_id"])
    except ProviderError as err:
        _LOGGER.warning("Club information unavailable: %s", type(err).__name__)
        connection.send_error(msg["id"], "provider_error", "Club information unavailable")
        return
    try:
        roster = await provider.roster(msg["team_id"])
    except ProviderError:
        # A missing roster must not hide an otherwise valid club profile.
        _LOGGER.debug("Roster unavailable for a requested club")
        roster = []
    connection.send_result(msg["id"], {**club, "roster": roster})


@websocket_api.websocket_command({"type": "football_news/club_brief", probatio.Required("team_id"): str, probatio.Required("league"): str})
@websocket_api.async_response
async def ws_club_brief(hass: HomeAssistant, connection, msg):
    """Lightweight club identity: never fetch the full roster for card lists."""
    runtime = _league_runtime(hass, msg["league"])
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    try:
        club = await runtime["coordinator"].provider.club(msg["team_id"])
    except ProviderError as err:
        _LOGGER.debug("Club brief unavailable: league=%s reason=%s",msg["league"],type(err).__name__)
        connection.send_error(msg["id"], "provider_error", "Club profile unavailable")
        return
    connection.send_result(msg["id"], club)


@websocket_api.websocket_command({"type": "football_news/leaders", probatio.Required("league"): str})
@websocket_api.async_response
async def ws_leaders(hass: HomeAssistant, connection, msg):
    runtime = _league_runtime(hass, msg["league"])
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    try:
        leaders = await runtime["coordinator"].provider.leaders()
    except ProviderError as error:
        # ESPN may reject undocumented endpoints or return a layout we do not
        # recognize. The domain/HTTP status are safe to expose for diagnosis;
        # do not log personal data or request headers.
        _LOGGER.warning("Football News ESPN player leaders failed league=%s: %s",
                        msg["league"], str(error)[:220])
        connection.send_error(msg["id"], "provider_error", str(error)[:190])
        return
    # Athlete portraits are no longer rendered in the football dashboard;
    # omit URLs from WebSocket payloads to keep responses small.
    rows=[{key:value for key,value in item.items() if key != "photo"} for item in leaders]
    connection.send_result(msg["id"], {"league": msg["league"], "leaders": rows})


@websocket_api.websocket_command({"type": "football_news/toggle_favourite", probatio.Required("kind"): str, probatio.Required("league"): str, probatio.Optional("team_id"): str, probatio.Optional("name"): str, probatio.Optional("event_id"): str})
@websocket_api.async_response
async def ws_toggle_favourite(hass: HomeAssistant, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    if msg["league"] not in LEAGUES:
        connection.send_error(msg["id"], "invalid", "Unknown league")
        return
    if msg["kind"] not in ("club", "league", "match"):
        connection.send_error(msg["id"], "invalid", "Unknown preference type")
        return
    prefs = hass.data[DOMAIN]["preferences"]
    try:
        if msg["kind"] == "club":
            await prefs.toggle_club(msg["league"], msg.get("team_id", ""), msg.get("name", ""))
        elif msg["kind"] == "match":
            await prefs.toggle_match(msg["league"], msg.get("event_id", ""))
        else:
            await prefs.toggle_league(msg["league"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], await prefs.read())


@websocket_api.websocket_command({
    "type": "football_news/set_favourite",
    probatio.Required("league"): str,
    probatio.Required("team_id"): str,
    probatio.Required("name"): str,
    probatio.Required("enabled"): bool,
})
@websocket_api.async_response
async def ws_set_favourite(hass: HomeAssistant, connection, msg):
    """Persist club preferences with explicit target state and saved acknowledgement."""
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    if msg["league"] not in LEAGUES:
        connection.send_error(msg["id"], "invalid", "Unknown competition")
        return
    try:
        saved = await hass.data[DOMAIN]["preferences"].set_club(
            msg["league"], msg["team_id"], msg["name"], msg["enabled"])
    except (ValueError, OSError) as err:
        _LOGGER.warning("Football News favourite save failed: %s", type(err).__name__)
        connection.send_error(msg["id"], "save_failed", str(err)[:150])
        return
    connection.send_result(msg["id"], saved)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static resources and actions only; never contact upstream here."""
    hass.data.setdefault(DOMAIN, {"entries": {}})
    hass.data[DOMAIN]["preferences"] = FootballPreferences(hass)
    await hass.http.async_register_static_paths([
        StaticPathConfig("/football_news/assets", str(_ROOT / "frontend"), False),
        StaticPathConfig("/football_news/panel.js", str(_ROOT / "frontend" / "panel.js"), False),
        StaticPathConfig("/football_news/icon.png", str(_ROOT / "brand" / "icon.png"), False),
    ])
    await async_register_panel(
        hass,
        frontend_url_path="football-news",
        webcomponent_name="football-news-panel",
        sidebar_title="Football News",
        sidebar_icon="mdi:soccer",
        module_url=f"/football_news/assets/panel_entry.js?v={VERSION}",
        require_admin=False,
    )
    websocket_api.async_register_command(hass, ws_get_data)
    websocket_api.async_register_command(hass, ws_quick_setup)
    websocket_api.async_register_command(hass, ws_reload_entries)
    websocket_api.async_register_command(hass, ws_teams)
    websocket_api.async_register_command(hass, ws_match)
    websocket_api.async_register_command(hass, ws_fixtures_month)
    websocket_api.async_register_command(hass, ws_club)
    websocket_api.async_register_command(hass, ws_leaders)
    websocket_api.async_register_command(hass, ws_club_brief)
    websocket_api.async_register_command(hass, ws_toggle_favourite)
    websocket_api.async_register_command(hass, ws_set_favourite)

    async def refresh(call: ServiceCall):
        entry_id = call.data.get("entry_id", "")
        entries = hass.data.get(DOMAIN, {}).get("entries", {})
        if entry_id:
            runtime = entries.get(entry_id)
            if not runtime:
                raise HomeAssistantError("Football News config entry not found")
            await runtime["coordinator"].async_request_refresh()
        elif entries:
            # Dashboard refresh is global and must not update only league #1.
            await asyncio.gather(*(runtime["coordinator"].async_request_refresh()
                                   for runtime in entries.values()))
        else:
            raise HomeAssistantError("No Football News competitions configured")

    async def test_zalo(call: ServiceCall):
        runtime = _runtime(hass, call.data.get("entry_id", ""))
        if not runtime:
            raise HomeAssistantError("Football News config entry not found")
        sent = await runtime["notifier"].send(
            "{big}{green}**⚽ FOOTBALL NEWS**{/green}{/big}\n"
            "✅ Kết nối thông báo Zalo thành công!\n"
            "{small}Tin nhắn thử từ Home Assistant{/small}"
        )
        if not sent:
            raise HomeAssistantError("Zalo send failed: verify options and zalo_bot integration/logs")

    async def match_details(call: ServiceCall):
        runtime = _runtime(hass, call.data.get("entry_id", ""))
        if not runtime:
            raise HomeAssistantError("Football News config entry not found")
        try:
            payload = await runtime["coordinator"].provider.summary(str(call.data["event_id"]))
        except ProviderError as err:
            raise HomeAssistantError(str(err)) from err
        header = payload.get("header") or {}
        boxscore = payload.get("boxscore") or {}
        return {
            "provider": "ESPN", "event_id": str(call.data["event_id"]),
            "header": header, "boxscore": boxscore,
            "key_events": payload.get("keyEvents", [])[:40],
            "scoring_plays": payload.get("scoringPlays", [])[:40],
        }

    hass.services.async_register(DOMAIN, "refresh", refresh, schema=vol.Schema({vol.Optional("entry_id"): str}))
    hass.services.async_register(DOMAIN, "test_zalo", test_zalo, schema=vol.Schema({vol.Optional("entry_id"): str}))
    hass.services.async_register(
        DOMAIN, "match_details", match_details,
        schema=vol.Schema({vol.Required("event_id"): str, vol.Optional("entry_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    _LOGGER.info("Football News %s registered without startup network I/O", VERSION)
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Do not await ESPN/Zalo during HA startup; populate entities afterwards."""
    league = entry.data["league"]
    # One-time migration: discard old provider credentials/flags from HA storage.
    obsolete = {"api_football_key", "use_football_hub_data", "clear_api_football_key"}
    if obsolete.intersection(entry.options):
        hass.config_entries.async_update_entry(
            entry, options={key: value for key, value in entry.options.items() if key not in obsolete}
        )
        _LOGGER.info("Football News removed obsolete player-provider settings league=%s", league)
    provider = FootballProvider(async_get_clientsession(hass), league)
    coordinator = FootballNewsCoordinator(hass, entry, provider)
    notifier = ZaloNotifier(hass, entry, LEAGUES.get(league, league))
    coordinator.notifier = notifier
    entry.runtime_data = {"coordinator": coordinator, "notifier": notifier}
    hass.data.setdefault(DOMAIN, {"entries": {}})["entries"][entry.entry_id] = {
        "entry": entry, "coordinator": coordinator, "notifier": notifier,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def start_refresh(event=None):
        hass.async_create_task(coordinator.async_refresh())
        hass.async_create_task(hass.data[DOMAIN]["preferences"].read())

    if hass.is_running:
        start_refresh()
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_refresh))
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry) -> None:
    """Apply native options without forcing a costly network request at startup."""
    # Filters and notifications read entry.options on each refresh; language is fetched on UI reload.
    _LOGGER.debug("Football News options updated for entry %s", entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
    return unloaded
