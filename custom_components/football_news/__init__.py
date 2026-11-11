"""Football News - independent, privacy-aware Home Assistant integration."""
from __future__ import annotations

import logging
from pathlib import Path

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .const import DOMAIN, VERSION, LEAGUES
from .coordinator import FootballNewsCoordinator
from .notifications import ZaloNotifier
from .provider import FootballProvider, ProviderError
from .models import normalize_summary
from .preferences import FootballPreferences
from .predictions import PredictionsStore

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ("sensor", "binary_sensor")
_ROOT = Path(__file__).parent


def _runtime(hass: HomeAssistant, entry_id: str = ""):
    entries = hass.data.get(DOMAIN, {}).get("entries", {})
    if entry_id:
        return entries.get(entry_id)
    return next(iter(entries.values()), None)


@websocket_api.websocket_command({"type": "football_news/data", vol.Optional("entry_id"): str})
@websocket_api.async_response
async def ws_get_data(hass: HomeAssistant, connection, msg):
    """Authenticated frontend snapshot, without leaking Zalo destination IDs."""
    runtime = _runtime(hass, msg.get("entry_id", ""))
    if not runtime:
        connection.send_error(msg["id"], "not_found", "Football News not configured")
        return
    coordinator = runtime["coordinator"]
    data = coordinator.data or {"fixtures": [], "standings": [], "news": [], "updated_at": {}, "errors": []}
    leagues = []
    for other in hass.data[DOMAIN]["entries"].values():
        other_coordinator = other["coordinator"]
        code = other_coordinator.provider.league
        snapshot = other_coordinator.data or {}
        leagues.append({"league_code": code, "name": LEAGUES.get(code, code),
                        "fixtures": snapshot.get("fixtures", [])[:350],
                        "standings": snapshot.get("standings", [])[:60],
                        "news": snapshot.get("news", [])[:25],
                        "updated_at": snapshot.get("updated_at", {}),
                        "errors": snapshot.get("errors", [])[:3]})
    preferences = await hass.data[DOMAIN]["preferences"].read()
    connection.send_result(msg["id"], {
        **data,
        "league": LEAGUES.get(coordinator.provider.league, coordinator.provider.league),
        "entry_id": runtime["entry"].entry_id,
        "language": runtime["entry"].options.get("locale", "vi"),
        "leagues": leagues, "preferences": preferences,
        "admin": bool(connection.user.is_admin),
    })


@websocket_api.websocket_command({"type": "football_news/match", vol.Required("event_id"): str, vol.Optional("entry_id"): str, vol.Optional("league"): str})
@websocket_api.async_response
async def ws_match(hass: HomeAssistant, connection, msg):
    """Fetch optional match statistics only when a viewer requests them."""
    runtime = _runtime(hass, msg.get("entry_id", ""))
    code = msg.get("league")
    if code:
        runtime = next((r for r in hass.data[DOMAIN]["entries"].values()
                        if r["coordinator"].provider.league == code), None)
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


@websocket_api.websocket_command({"type": "football_news/fixtures_month", vol.Required("month"): str, vol.Required("league"): str})
@websocket_api.async_response
async def ws_fixtures_month(hass: HomeAssistant, connection, msg):
    runtime = next((r for r in hass.data.get(DOMAIN, {}).get("entries", {}).values()
                    if r["coordinator"].provider.league == msg["league"]), None)
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    try:
        matches = await runtime["coordinator"].provider.fixtures_month(msg["month"])
    except ProviderError:
        connection.send_error(msg["id"], "provider_error", "Monthly fixtures unavailable")
        return
    connection.send_result(msg["id"], {"league": msg["league"], "month": msg["month"],
                                        "fixtures": matches[:500]})


@websocket_api.websocket_command({"type": "football_news/club", vol.Required("team_id"): str, vol.Required("league"): str})
@websocket_api.async_response
async def ws_club(hass: HomeAssistant, connection, msg):
    runtime = next((r for r in hass.data.get(DOMAIN, {}).get("entries", {}).values()
                    if r["coordinator"].provider.league == msg["league"]), None)
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


@websocket_api.websocket_command({"type": "football_news/leaders", vol.Required("league"): str})
@websocket_api.async_response
async def ws_leaders(hass: HomeAssistant, connection, msg):
    runtime = next((r for r in hass.data.get(DOMAIN, {}).get("entries", {}).values()
                    if r["coordinator"].provider.league == msg["league"]), None)
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    try:
        leaders = await runtime["coordinator"].provider.leaders()
    except ProviderError:
        connection.send_error(msg["id"], "provider_error", "Leader table unavailable")
        return
    connection.send_result(msg["id"], {"league": msg["league"], "leaders": leaders})


@websocket_api.websocket_command({"type": "football_news/toggle_favourite", vol.Required("kind"): vol.In(["club", "league", "match"]), vol.Required("league"): str, vol.Optional("team_id"): str, vol.Optional("name"): str, vol.Optional("event_id"): str})
@websocket_api.async_response
async def ws_toggle_favourite(hass: HomeAssistant, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    if msg["league"] not in LEAGUES:
        connection.send_error(msg["id"], "invalid", "Unknown league")
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


@websocket_api.websocket_command({"type": "football_news/competitions"})
@websocket_api.async_response
async def ws_competitions(hass: HomeAssistant, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator required")
        return
    connection.send_result(msg["id"], {"competitions": await hass.data[DOMAIN]["predictions"].all()})


async def _admin_only(hass: HomeAssistant, context) -> None:
    if context.user_id:
        user = await hass.auth.async_get_user(context.user_id)
        if not user or not user.is_admin:
            raise HomeAssistantError("Only Home Assistant administrators may manage competitions")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static resources and actions only; never contact upstream here."""
    hass.data.setdefault(DOMAIN, {"entries": {}})
    hass.data[DOMAIN]["preferences"] = FootballPreferences(hass)
    hass.data[DOMAIN]["predictions"] = PredictionsStore(hass)
    await hass.http.async_register_static_paths([
        StaticPathConfig("/football_news/panel.js", str(_ROOT / "frontend" / "panel.js"), False),
        StaticPathConfig("/football_news/icon.png", str(_ROOT / "brand" / "icon.png"), False),
    ])
    async_register_built_in_panel(
        hass, component_name="custom", sidebar_title="Football News",
        sidebar_icon="mdi:soccer", frontend_url_path="football-news",
        config={"_panel_custom": {
            "name": "football-news-panel",
            "module_url": f"/football_news/panel.js?v={VERSION}",
            "embed_iframe": False, "trust_external": False,
        }}, require_admin=False, update="football-news" in hass.data.get("frontend_panels", {}),
    )
    websocket_api.async_register_command(hass, ws_get_data)
    websocket_api.async_register_command(hass, ws_match)
    websocket_api.async_register_command(hass, ws_fixtures_month)
    websocket_api.async_register_command(hass, ws_club)
    websocket_api.async_register_command(hass, ws_leaders)
    websocket_api.async_register_command(hass, ws_toggle_favourite)
    websocket_api.async_register_command(hass, ws_competitions)

    async def refresh(call: ServiceCall):
        runtime = _runtime(hass, call.data.get("entry_id", ""))
        if runtime:
            await runtime["coordinator"].async_request_refresh()
        else:
            raise HomeAssistantError("Football News config entry not found")

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

    async def manage_competition(call: ServiceCall):
        await _admin_only(hass, call.context)
        try:
            return await hass.data[DOMAIN]["predictions"].mutate(call.data["operation"], dict(call.data))
        except (ValueError, KeyError, TypeError) as err:
            raise HomeAssistantError(f"Competition validation failed: {err}") from err

    async def get_competitions(call: ServiceCall):
        await _admin_only(hass, call.context)
        return {"competitions": await hass.data[DOMAIN]["predictions"].all()}

    hass.services.async_register(
        DOMAIN, "manage_competition", manage_competition,
        schema=vol.Schema({
            vol.Required("operation"): vol.In(["create", "add_player", "round", "pick", "payment", "buyback"]),
            vol.Optional("competition_id"): str,
            vol.Optional("kind"): vol.In(["lms", "acca"]),
            vol.Optional("title"): str, vol.Optional("league"): vol.In(LEAGUES),
            vol.Optional("player_id"): str, vol.Optional("player_name"): str,
            vol.Optional("round_id"): str, vol.Optional("deadline"): str,
            vol.Optional("fixture_ids"): [str], vol.Optional("picks"): [dict],
            vol.Optional("amount"): vol.Coerce(float),
        }), supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "get_competitions", get_competitions, supports_response=SupportsResponse.ONLY,
    )
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
    provider = FootballProvider(async_get_clientsession(hass), league)
    coordinator = FootballNewsCoordinator(hass, entry, provider)
    notifier = ZaloNotifier(hass, entry, LEAGUES.get(league, league))
    coordinator.notifier = notifier
    coordinator.predictions = hass.data[DOMAIN]["predictions"]
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
