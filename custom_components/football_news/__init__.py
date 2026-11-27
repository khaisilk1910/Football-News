"""Football News - independent, privacy-aware Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from time import monotonic

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
from .ui_state import FootballUIState
from .snapshot import competition_snapshot, runtime_for_entry
from .cold_start import FootballColdStartCache
from .registry import FootballLeagueRegistry
from .recovery import FootballSavedCacheRecovery
from .store_first import async_store_first_snapshot

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




def _start_panel_cache_warm(hass: HomeAssistant, known_entries: list) -> None:
    """Warm the LOCAL cache outside the WebSocket response critical path.

    A Companion first-open must receive a WS response even when config entries
    and HA Store are still restoring. One shared task serves all devices; a
    second panel does not launch a competing scan or network fetch.
    """
    state = hass.data.get(DOMAIN)
    if state is None:
        return
    running = state.get("panel_cache_warm_task")
    if running is not None and not running.done():
        return
    now = monotonic()
    if now < state.get("panel_cache_retry_after", 0):
        return

    async def warm() -> None:
        entries = list(known_entries)
        snapshots: dict[str, dict] = {}
        try:
            if not entries:
                registry = state.get("league_registry")
                if registry is not None:
                    entries = await registry.fallback_entries()
            if not entries:
                recovery = state.get("saved_cache_recovery")
                if recovery is not None:
                    found = await recovery.async_snapshots()
                    entries = [item for item, _ in found]
                    snapshots = {item.entry_id: saved for item, saved in found}
            cold = state.get("cold_cache")
            if cold is not None and entries:
                runtimes = state.get("entries", {})
                async def one(entry):
                    runtime = runtime_for_entry(entry, runtimes)
                    data = getattr(runtime.get("coordinator"), "data", {}) if runtime else {}
                    if all(data.get(name) for name in ("fixtures", "standings")):
                        return entry.entry_id, {}
                    return entry.entry_id, await cold.async_entry_snapshot(entry)
                results = await asyncio.gather(*(one(entry) for entry in entries), return_exceptions=True)
                for result in results:
                    if not isinstance(result, BaseException) and result[1]:
                        snapshots[result[0]] = result[1]
            state["panel_cache_warm_entries"] = entries
            state["panel_cache_warm_snapshots"] = snapshots
            ready = sum(bool(item) for item in snapshots.values())
            _LOGGER.info("Football News panel HA Store warm completed: leagues=%d disk_snapshots=%d",
                         len(entries), ready)
        except Exception:
            _LOGGER.exception("Football News initial panel cache warm failed")
        finally:
            # A retry on a later visit is allowed: e.g. HA registry not yet
            # restored when the very first phone connection arrived.
            state["panel_cache_retry_after"] = monotonic() + (12 if not entries else 30)
            hass.bus.async_fire(f"{DOMAIN}_data_updated", {"phase": "panel_cache_warm"})

    creator = getattr(hass, "async_create_task", asyncio.create_task)
    state["panel_cache_warm_task"] = creator(warm())

@websocket_api.websocket_command({"type": "football_news/data", probatio.Optional("entry_id"): str, probatio.Optional("fast"): bool, probatio.Optional("store_refresh"): bool})
@websocket_api.async_response
async def ws_get_data(hass: HomeAssistant, connection, msg):
    """Authenticated frontend snapshot, without leaking Zalo destination IDs."""
    # Settings can already contain six leagues while their async_setup_entry
    # is loading/retrying. The config-entry registry, not hass.data runtimes,
    # is the source of truth for the configured count.
    configured = list(hass.config_entries.async_entries(DOMAIN))
    # On the first sidebar visit HA can still be restoring its config-entry
    # registry. A bounded local wait only affects this WebSocket request, never
    # Home Assistant startup; no ESPN/network request is made here.
    startup_pending = not getattr(hass, "is_running", True)
    runtimes = hass.data.get(DOMAIN, {}).get("entries", {})
    # The very first panel visit gets its own full 120-second grace period.
    # Subsequent tabs/reloads must not restart the clock or interrupt ongoing
    # Live polling on a previously refreshed Home Assistant installation.
    for runtime in runtimes.values():
        if isinstance(runtime, dict):
            coordinator = runtime.get("coordinator")
            visit = getattr(coordinator, "note_panel_visit", None)
            if callable(visit):
                visit()
    # Both the first screen and subsequent refreshes read the authoritative
    # HA Store *before* considering any coordinator RAM. A response is never
    # blocked by ESPN or an unfinished config-entry setup. Store reads for the
    # same league are deduplicated across connected devices.
    preferences_task = None
    ui_task = None
    if not msg.get("fast"):
        preference_store = hass.data.get(DOMAIN, {}).get("preferences")
        if preference_store is not None:
            preferences_task = asyncio.create_task(preference_store.read())
        ui_store = hass.data.get(DOMAIN, {}).get("ui_state")
        user_id = getattr(connection.user, "id", None)
        if ui_store is not None and user_id:
            ui_task = asyncio.create_task(ui_store.read(user_id))
    # A cold HA Store read is authoritative, but must not hold the first
    # Companion WebSocket message indefinitely. Reuse one in-flight disk task
    # across clients, give it a short foreground budget, then notify subscribers
    # when it eventually finishes. No ESPN I/O is started here.
    state = hass.data.get(DOMAIN, {})
    key = tuple(sorted((item.entry_id, item.data.get("league", "")) for item in configured))
    store_task = state.get("panel_store_first_read_task")
    if (store_task is None or store_task.done() or
            state.get("panel_store_first_read_key") != key or msg.get("store_refresh")):
        store_task = asyncio.create_task(async_store_first_snapshot(hass, configured))
        state["panel_store_first_read_task"] = store_task
        state["panel_store_first_read_key"] = key

        def store_finished(task):
            # Only an unfinished WebSocket request needs a wake-up event.
            # Broadcasting on every normal read would cause a retry loop.
            waiting = state.get("panel_store_first_read_waiters", set())
            if task not in waiting:
                return
            waiting.discard(task)
            try:
                task.result()
            except Exception:
                _LOGGER.exception("Football News HA Store background read failed")
            bus = getattr(hass, "bus", None)
            if callable(getattr(bus, "async_fire", None)):
                bus.async_fire(f"{DOMAIN}_data_updated", {"phase": "store_read_complete"})

        store_task.add_done_callback(store_finished)
    try:
        configured, saved, store_status = await asyncio.wait_for(
            asyncio.shield(store_task), timeout=6 if msg.get("fast") else 10)
    except asyncio.TimeoutError:
        # The disk task stays alive, but the browser gets a *real* HA response
        # with whatever the coordinator has, rather than being stuck forever.
        state.setdefault("panel_store_first_read_waiters", set()).add(store_task)
        saved = {}
        store_status = {"store_attempted": len(configured), "store_restored": 0,
                        "store_errors": 0, "registry_fallback": False,
                        "recovery_fallback": False, "store_pending": True}
        _LOGGER.warning("Football News HA Store read still pending; returning coordinator snapshot "
                        "to first-view WebSocket (configured=%d)", len(configured))
    except Exception:
        saved = {}
        store_status = {"store_attempted": len(configured), "store_restored": 0,
                        "store_errors": 1, "registry_fallback": False,
                        "recovery_fallback": False, "store_pending": False}
        _LOGGER.exception("Football News HA Store first-view read failed")
    runtimes = hass.data.get(DOMAIN, {}).get("entries", {})
    leagues = competition_snapshot(configured, runtimes, LEAGUES, saved)
    if msg.get("fast"):
        selected = next((row for row in leagues if row.get("ready")), None) or (leagues[0] if leagues else {})
        cache_ready = any(row.get("ready") for row in leagues)
        _LOGGER.info("Football News first-view HA Store result leagues=%d restored=%d ready=%s errors=%d",
                     len(configured), store_status["store_restored"], cache_ready,
                     store_status["store_errors"])
        connection.send_result(msg["id"], {
            "leagues": leagues,
            "fixtures": selected.get("fixtures", []),
            "standings": selected.get("standings", []),
            "news": selected.get("news", []),
            "updated_at": selected.get("updated_at", {}),
            "preferences": {"clubs": [], "matches": [], "leagues": []},
            "ui_state": {"tab": "overview", "league": "all", "style": "auto", "revision": -1},
            "configured_count": len(configured),
            "startup_pending": startup_pending,
            "bootstrap_partial": True,
            "cache_state": ("available" if cache_ready else
                            "restoring" if store_status.get("store_pending") or configured or startup_pending
                            else "pending_setup"),
            "cache_source": "ha_store" if store_status["store_restored"] else "memory" if cache_ready else "none",
            "espn_wait_seconds": max((runtime["coordinator"].espn_wait_seconds()
                for runtime in runtimes.values() if isinstance(runtime, dict) and
                callable(getattr(runtime.get("coordinator"), "espn_wait_seconds", None))), default=0),
            "backend_version": VERSION,
            "recovery_status": {"native_entries": len(hass.config_entries.async_entries(DOMAIN)),
                "restored_feeds": sum(bool(row.get("fixtures") or row.get("standings") or row.get("news")) for row in leagues),
                **store_status},
            "admin": bool(connection.user and connection.user.is_admin),
        })
        return
    registry_fallback = store_status["registry_fallback"] or store_status["recovery_fallback"]
    recovered_saved = [(ent, saved[ent.entry_id]) for ent in configured
                       if ent.entry_id in saved and saved[ent.entry_id]]
    if not leagues and not startup_pending:
        state = hass.data.get(DOMAIN, {})
        now = monotonic()
        if now - state.get("_no_leagues_warning_at", -120) >= 60:
            state["_no_leagues_warning_at"] = now
            _LOGGER.warning("Football News HA Store has no usable league snapshot: entries=%d "
                            "restored=%d errors=%d. Verify config entries and .storage; "
                            "no ESPN call was made.", len(configured),
                            store_status["store_restored"], store_status["store_errors"])
    runtime = _runtime(hass, msg.get("entry_id", ""))
    if not runtime and configured:
        runtime = next((runtime_for_entry(entry, runtimes) for entry in configured
                        if runtime_for_entry(entry, runtimes)), None)
    coordinator = runtime["coordinator"] if runtime else None
    current = (coordinator.data if coordinator else None) or {}
    # The top-level legacy fields must also serve disk-only leagues. Previously
    # they stayed empty until a coordinator existed, even though `leagues`
    # already contained the valid .storage snapshot.
    requested_entry = msg.get("entry_id", "")
    selected = next((row for row in leagues if row["entry_id"] == requested_entry), None)
    if selected is None and runtime:
        selected = next((row for row in leagues if row["entry_id"] == runtime["entry"].entry_id), None)
    if selected is None:
        selected = next((row for row in leagues if row["ready"]), None) or (leagues[0] if leagues else {})
    data = {"fixtures": selected.get("fixtures", []),
            "standings": selected.get("standings", []),
            "news": selected.get("news", []),
            "updated_at": selected.get("updated_at", {}),
            "cache_info": selected.get("cache_info", {}),
            "errors": selected.get("errors", [])}
    preferences = {"clubs": [], "matches": [], "leagues": []}
    if preferences_task is not None:
        try:
            preferences = await asyncio.wait_for(preferences_task, timeout=2)
        except Exception as err:
            _LOGGER.warning("Football News preferences unavailable during snapshot: %s", type(err).__name__)
    # Profile preferences are optional and never allowed to block football
    # cache restoration. Their reads started while the league files loaded.
    ui_state = {"tab": "overview", "league": "all", "style": "auto", "revision": 0}
    if ui_task is not None:
        try:
            ui_state = await asyncio.wait_for(ui_task, timeout=2)
        except Exception as err:
            _LOGGER.warning("Football News UI state read failed: %s", type(err).__name__)
    lang_entry = runtime["entry"] if runtime else (configured[0] if configured else None)
    connection.send_result(msg["id"], {
        **data,
        "league": selected.get("name", ""),
        "entry_id": selected.get("entry_id", ""),
        "language": lang_entry.options.get("locale", "vi") if lang_entry else "vi",
        "leagues": leagues,
        "preferences": preferences,
        "ui_state": ui_state,
        "starter_leagues": [{"code": code, "name": LEAGUES[code]} for code in STARTER_LEAGUES],
        "configured_count": len(configured),
        "startup_pending": startup_pending,
        "registry_fallback": registry_fallback,
        "registry_source": "saved_cache_files" if store_status["recovery_fallback"] else (
            "saved_ha" if registry_fallback else "config_entries"),
        "backend_version": VERSION,
        "cache_source": "ha_store" if store_status["store_restored"] else "memory" if any(row.get("ready") for row in leagues) else "none",
        "cache_state": ("available" if any(row.get("ready") for row in leagues) else
                        "restoring" if store_status.get("store_pending") else
                        "empty" if configured else "pending_setup"),
        "espn_wait_seconds": max((runtime["coordinator"].espn_wait_seconds()
                                  for runtime in runtimes.values()
                                  if isinstance(runtime, dict) and
                                  callable(getattr(runtime.get("coordinator"), "espn_wait_seconds", None))), default=0),
        "recovery_status": {
            "native_entries": len(hass.config_entries.async_entries(DOMAIN)),
            "saved_only_entries": len(recovered_saved),
            "restored_feeds": sum(bool(row.get('fixtures') or row.get('standings') or row.get('news')) for row in leagues),
            **store_status,
        },
        "runtime_count": sum(1 for row in leagues if row["runtime_loaded"]),
        "admin": bool(connection.user and connection.user.is_admin),
    })


@websocket_api.websocket_command({
    "type": "football_news/set_ui_state",
    probatio.Optional("tab"): str,
    probatio.Optional("league"): str,
    probatio.Optional("style"): str,
})
@websocket_api.async_response
async def ws_set_ui_state(hass: HomeAssistant, connection, msg):
    """Save appearance/navigation for this HA account, shared across devices."""
    if not connection.user:
        connection.send_error(msg["id"], "unauthorized", "Authentication required")
        return
    changes = {key: msg[key] for key in ("tab", "league", "style") if key in msg}
    try:
        saved = await hass.data[DOMAIN]["ui_state"].update(connection.user.id, changes)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    except Exception as err:
        _LOGGER.exception("Football News UI state save failed, user authenticated=%s", bool(connection.user))
        connection.send_error(msg["id"], "save_failed", "Home Assistant storage write failed")
        return
    connection.send_result(msg["id"], saved)


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


@websocket_api.websocket_command({"type": "football_news/match_roster",
                                      probatio.Required("team_id"): str,
                                      probatio.Required("league"): str})
@websocket_api.async_response
async def ws_match_roster(hass: HomeAssistant, connection, msg):
    """Optional season squad, loaded ONLY when a viewer opens match lineups.

    The frontend compares these athletes against ESPN's match-sheet IDs to
    identify players not named in that match. It never runs at HA startup.
    The provider caches the club squad for 12 hours across viewing devices.
    """
    runtime = _league_runtime(hass, msg["league"])
    if not runtime:
        connection.send_error(msg["id"], "not_found", "League not configured")
        return
    try:
        players = await runtime["coordinator"].provider.roster(msg["team_id"])
    except ProviderError as err:
        _LOGGER.debug("Match season-roster unavailable league=%s team=%s: %s",
                      msg["league"], msg["team_id"], type(err).__name__)
        connection.send_error(msg["id"], "provider_error", "Season roster unavailable")
        return
    connection.send_result(msg["id"], {"team_id": msg["team_id"], "players": players})


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


@websocket_api.websocket_command({"type": "football_news/favourite_form", probatio.Required("league"): str})
@websocket_api.async_response
async def ws_favourite_form(hass: HomeAssistant, connection, msg):
    """On-demand 10-match form for all saved clubs in ONE competition.

    This never blocks HA startup and never lets a browser choose arbitrary
    teams to scan. Shared provider month caches avoid one request per device.
    """
    league = msg["league"]
    runtime = _league_runtime(hass, league)
    if not runtime:
        connection.send_error(msg["id"], "not_found", "Competition not configured")
        return
    try:
        saved = await hass.data[DOMAIN]["preferences"].read()
    except (OSError, ValueError, TypeError) as error:
        _LOGGER.warning("Favourite form preferences unavailable league=%s cause=%s",
                        league, type(error).__name__)
        connection.send_error(msg["id"], "storage_error", "Club preferences are unavailable")
        return
    clubs = [club for club in saved.get("clubs", [])
             if isinstance(club, dict) and club.get("league") == league]
    team_ids = [str(club.get("id", "")) for club in clubs[:5]]
    coordinator = runtime["coordinator"]
    try:
        result = await coordinator.async_favourite_form(team_ids)
    except ProviderError as error:
        _LOGGER.warning("Favourite form history unavailable league=%s cause=%s",
                        league, type(error).__name__)
        connection.send_error(msg["id"], "provider_error", "Recent fixtures unavailable")
        return
    connection.send_result(msg["id"], {"league": league, "team_ids": team_ids,
                                         **result})


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
        leaders, from_cache = await runtime["coordinator"].async_leaders()
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
    connection.send_result(msg["id"], {"league": msg["league"], "leaders": rows,
                                      "from_cache": from_cache})


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
    except (OSError, TypeError) as err:
        _LOGGER.warning("Football News favourite write failed: %s", type(err).__name__)
        connection.send_error(msg["id"], "save_failed", "Home Assistant storage write failed")
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
    hass.data[DOMAIN]["ui_state"] = FootballUIState(hass)
    hass.data[DOMAIN]["cold_cache"] = FootballColdStartCache(hass)
    hass.data[DOMAIN]["league_registry"] = FootballLeagueRegistry(hass)
    hass.data[DOMAIN]["saved_cache_recovery"] = FootballSavedCacheRecovery(hass)
    await hass.http.async_register_static_paths([
        StaticPathConfig("/football_news/assets", str(_ROOT / "frontend"), False),
        StaticPathConfig("/football_news/panel.js", str(_ROOT / "frontend" / "panel.js"), False),
        StaticPathConfig("/football_news/icon.png", str(_ROOT / "brand" / "icon.png"), False),
    ])
    websocket_api.async_register_command(hass, ws_get_data)
    websocket_api.async_register_command(hass, ws_set_ui_state)
    websocket_api.async_register_command(hass, ws_quick_setup)
    websocket_api.async_register_command(hass, ws_reload_entries)
    websocket_api.async_register_command(hass, ws_teams)
    websocket_api.async_register_command(hass, ws_match)
    websocket_api.async_register_command(hass, ws_match_roster)
    websocket_api.async_register_command(hass, ws_fixtures_month)
    websocket_api.async_register_command(hass, ws_club)
    websocket_api.async_register_command(hass, ws_leaders)
    websocket_api.async_register_command(hass, ws_club_brief)
    websocket_api.async_register_command(hass, ws_favourite_form)
    websocket_api.async_register_command(hass, ws_toggle_favourite)
    websocket_api.async_register_command(hass, ws_set_favourite)
    # Publish the sidebar only after every custom WS command is registered.
    await async_register_panel(
        hass,
        frontend_url_path="football-news",
        webcomponent_name="football-news-panel",
        sidebar_title="Football News",
        sidebar_icon="mdi:soccer",
        module_url=f"/football_news/assets/panel_entry.js?v={VERSION}",
        require_admin=False,
    )

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
    _LOGGER.info("Football News %s ready: HA Store is authoritative; no startup ESPN I/O", VERSION)
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Do not await ESPN/Zalo during HA startup; populate entities afterwards."""
    league = entry.data["league"]
    # Remember durable IDs without waiting on ESPN and without delaying HA
    # startup for a storage write. This allows first-panel cache reads even
    # when the config-entry registry is temporarily empty on later reloads.
    hass.async_create_task(hass.data[DOMAIN]["league_registry"].remember([entry]))
    # One-time migration: discard old provider credentials/flags from HA storage.
    obsolete = {"api_football_key", "use_football_hub_data", "clear_api_football_key"}
    if obsolete.intersection(entry.options):
        hass.config_entries.async_update_entry(
            entry, options={key: value for key, value in entry.options.items() if key not in obsolete}
        )
        _LOGGER.info("Football News removed obsolete player-provider settings league=%s", league)
    provider = FootballProvider(async_get_clientsession(hass), league)
    coordinator = FootballNewsCoordinator(hass, entry, provider)
    coordinator.begin_cache_first_window(120)
    notifier = ZaloNotifier(hass, entry, LEAGUES.get(league, league), provider=provider)
    coordinator.notifier = notifier
    entry.runtime_data = {"coordinator": coordinator, "notifier": notifier}
    hass.data.setdefault(DOMAIN, {"entries": {}})["entries"][entry.entry_id] = {
        "entry": entry, "coordinator": coordinator, "notifier": notifier,
    }
    # IMPORTANT: finish the LOCAL .storage restore before any platform setup or
    # background ESPN task can observe an empty coordinator. This reads only
    # Home Assistant's disk, never the network. The WebSocket cold-cache path
    # independently serves panels opened while this entry is still setting up.
    await coordinator.async_restore_cache()
    # The first sidebar request may have arrived before this runtime was
    # registered. Wake already-open clients as soon as disk hydration ends;
    # do not wait for ESPN, entity platforms or a manual panel reload.
    hass.bus.async_fire(f"{DOMAIN}_data_updated", {"league": league, "phase": "cache_ready"})
    _LOGGER.debug("Football News initial cache ready league=%s entry_state=%s",
                  league, entry.state)

    @callback
    def broadcast_updated_data() -> None:
        # Emitted *after* coordinator data changes, never during ESPN fetch.
        # Other devices then read the same authoritative HA snapshot.
        if coordinator._last_visible_change:
            hass.bus.async_fire(f"{DOMAIN}_data_updated", {"league": league})

    entry.async_on_unload(coordinator.async_add_listener(broadcast_updated_data))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def start_refresh(event=None):
        # The first two minutes are *cache only*: the UI must see saved HA
        # Store data before upstream ESPN requests can replace any feed.
        # This is an async task, never a wait inside Home Assistant startup.
        async def refresh_after_cache_window():
            # A user opening the panel during HA startup can extend this once.
            # Re-evaluate after each sleep, not just at task creation.
            while (seconds := coordinator.espn_wait_seconds()):
                _LOGGER.info("Football News cache-first window league=%s waiting=%ss before ESPN",
                             league, seconds)
                await asyncio.sleep(seconds)
            await coordinator.async_refresh()
            await hass.data[DOMAIN]["preferences"].read()
        task = hass.async_create_task(refresh_after_cache_window())
        entry.async_on_unload(task.cancel)

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
        runtime = hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
        if runtime is not None:
            await runtime["coordinator"].async_stop_live_events()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry) -> None:
    """Discard the saved league index only on actual HA config-entry removal."""
    registry = hass.data.get(DOMAIN, {}).get("league_registry")
    if registry is not None:
        await registry.forget(entry.entry_id)
    state = hass.data.get(DOMAIN, {})
    state["panel_cache_warm_entries"] = [item for item in state.get("panel_cache_warm_entries", [])
                                          if item.entry_id != entry.entry_id]
    state.get("panel_cache_warm_snapshots", {}).pop(entry.entry_id, None)
