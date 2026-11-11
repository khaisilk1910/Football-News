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
    connection.send_result(msg["id"], {
        **data,
        "league": LEAGUES.get(coordinator.provider.league, coordinator.provider.league),
        "entry_id": runtime["entry"].entry_id,
        "language": runtime["entry"].options.get("locale", "vi"),
    })


@websocket_api.websocket_command({"type": "football_news/match", vol.Required("event_id"): str, vol.Optional("entry_id"): str})
@websocket_api.async_response
async def ws_match(hass: HomeAssistant, connection, msg):
    """Fetch optional match statistics only when a viewer requests them."""
    runtime = _runtime(hass, msg.get("entry_id", ""))
    if not runtime:
        connection.send_error(msg["id"], "not_found", "Football News not configured")
        return
    try:
        payload = await runtime["coordinator"].provider.summary(msg["event_id"])
    except ProviderError as err:
        _LOGGER.warning("On-demand match detail unavailable (%s)", type(err).__name__)
        connection.send_error(msg["id"], "provider_error", "Match details are unavailable")
        return
    connection.send_result(msg["id"], normalize_summary(payload))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static resources and actions only; never contact upstream here."""
    hass.data.setdefault(DOMAIN, {"entries": {}})
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
    entry.runtime_data = {"coordinator": coordinator, "notifier": notifier}
    hass.data.setdefault(DOMAIN, {"entries": {}})["entries"][entry.entry_id] = {
        "entry": entry, "coordinator": coordinator, "notifier": notifier,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def start_refresh(event=None):
        hass.async_create_task(coordinator.async_refresh())

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
