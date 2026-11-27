"""HA Store-first dashboard snapshots, shared between all connected clients.

Only reads HA's own Store API; never performs network I/O or modifies config.
This route is deliberately independent of the coordinator's startup state.
"""
from __future__ import annotations

import asyncio
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_store_first_snapshot(hass, configured: list) -> tuple[list, dict, dict]:
    """Load persisted league snapshots before falling back to runtime data.

    A multi-device first visit must not depend on whether the coordinator has
    already copied disk state into RAM. ColdStartCache deduplicates Store reads
    across concurrent WebSockets. Missing entry registries can be reconstructed
    read-only from the saved league index or verified cache files.
    """
    state = hass.data.get(DOMAIN, {})
    entries = list(configured)
    if not entries and not getattr(hass, "is_running", True):
        # During cold startup the HA registry can become ready just after the
        # first socket opened. Probe briefly before consulting saved indexes.
        for _ in range(3):
            await asyncio.sleep(0.2)
            entries = list(hass.config_entries.async_entries(DOMAIN))
            if entries:
                break
    known_ids = {item.entry_id for item in entries}
    runtimes = state.get("entries", {})
    for runtime in runtimes.values():
        ent = runtime.get("entry") if isinstance(runtime, dict) else None
        if ent is not None and ent.entry_id not in known_ids:
            entries.append(ent)
            known_ids.add(ent.entry_id)

    registry = state.get("league_registry")
    recovery = state.get("saved_cache_recovery")
    issues = {"store_attempted": 0, "store_restored": 0, "registry_fallback": False,
              "recovery_fallback": False, "store_errors": 0}
    recovery_cache = {}
    # The native entry registry can be only PARTIALLY ready during a HA cold
    # start. Merge the durable HA league index even if one native entry already
    # exists; otherwise the first view on a new device loses whole leagues.
    if registry is not None and (not entries or not getattr(hass, "is_running", True)):
        try:
            # An optional index must not block native Store snapshots on the
            # first sidebar visit when the HA registry is still starting.
            indexed = await asyncio.wait_for(registry.fallback_entries(), timeout=1.5)
            known_leagues = {ent.data.get("league") for ent in entries}
            for ent in indexed:
                league = ent.data.get("league")
                if ent.entry_id not in known_ids and league not in known_leagues:
                    entries.append(ent)
                    known_ids.add(ent.entry_id)
                    known_leagues.add(league)
                    issues["registry_fallback"] = True
        except Exception as err:
            issues["store_errors"] += 1
            _LOGGER.warning("Football News saved league index unavailable: %s", type(err).__name__)

    # When there are no indexed entries at all, discover verified HA Store
    # files directly. In particular, do NOT infer that an empty coordinator
    # means there are no saved competitions.
    if not entries and recovery is not None:
        try:
            found = await asyncio.wait_for(recovery.async_snapshots(), timeout=20)
            known_leagues = set()
            for ent, snapshot in found:
                league = ent.data.get("league")
                if ent.entry_id not in known_ids and league not in known_leagues:
                    entries.append(ent)
                    known_ids.add(ent.entry_id)
                    known_leagues.add(league)
                    recovery_cache[ent.entry_id] = snapshot
                    issues["recovery_fallback"] = True
        except Exception as err:
            issues["store_errors"] += 1
            _LOGGER.warning("Football News saved cache discovery unavailable: %s", type(err).__name__)

    cold = state.get("cold_cache")
    snapshots = dict(recovery_cache)
    if entries and cold is not None:
        async def read_one(ent):
            try:
                # The first panel query always reads HA Store. A slow disk read
                # continues after the short foreground WebSocket deadline and
                # its completion wakes all devices; do not return None after a
                # 7-second inner timeout and discard that eventual snapshot.
                return ent.entry_id, await asyncio.wait_for(
                    cold.async_entry_snapshot(ent, force=True), timeout=25)
            except asyncio.TimeoutError:
                _LOGGER.warning("Football News HA Store snapshot timed out league=%s", ent.data.get("league"))
                return ent.entry_id, None
            except Exception as err:
                _LOGGER.warning("Football News HA Store snapshot failed league=%s error=%s",
                                ent.data.get("league"), type(err).__name__)
                return ent.entry_id, None

        results = await asyncio.gather(*(read_one(item) for item in entries))
        issues["store_attempted"] = len(entries)
        for ent_id, saved in results:
            if saved is None:
                issues["store_errors"] += 1
            elif saved:
                snapshots[ent_id] = saved

    # A re-created config entry may have a new HA Store key for only SOME
    # leagues. Recover each missing competition independently, rather than
    # requiring all configured leagues to be missing at once.
    if entries and any(not snapshots.get(ent.entry_id) for ent in entries) and recovery is not None:
        # A missing file for league B must not delay valid disk fixtures for
        # league A. Run the read-only file scan once per HA instance; when it
        # finishes, notify every open panel to re-read the newly discovered
        # snapshots. New clients share the same server-side task.
        scan = state.get("panel_missing_cache_scan_task")
        if scan is None or scan.done():
            scan = asyncio.create_task(recovery.async_snapshots())
            state["panel_missing_cache_scan_task"] = scan

            def scan_done(task):
                try:
                    task.result()
                except Exception as err:
                    _LOGGER.warning("Football News saved cache scan failed: %s", type(err).__name__)
                if state.get("panel_missing_cache_scan_waiting"):
                    state["panel_missing_cache_scan_waiting"] = False
                    bus = getattr(hass, "bus", None)
                    if callable(getattr(bus, "async_fire", None)):
                        bus.async_fire(f"{DOMAIN}_data_updated", {"phase": "saved_cache_scan_complete"})

            scan.add_done_callback(scan_done)
        try:
            found = await asyncio.wait_for(asyncio.shield(scan), timeout=1.5)
            by_code = {ent.data.get("league"): snapshot for ent, snapshot in found if snapshot}
            for ent in entries:
                old = by_code.get(ent.data.get("league"))
                if old and not snapshots.get(ent.entry_id):
                    snapshots[ent.entry_id] = old
                    issues["recovery_fallback"] = True
        except asyncio.TimeoutError:
            issues["recovery_pending"] = True
            state["panel_missing_cache_scan_waiting"] = True
            _LOGGER.debug("Football News partial HA Store response while missing-cache scan runs")
        except Exception as err:
            issues["store_errors"] += 1
            _LOGGER.warning("Football News saved cache scan unavailable: %s", type(err).__name__)
    issues["store_restored"] = sum(bool(snapshots.get(ent.entry_id)) for ent in entries)
    _LOGGER.debug("Football News HA Store-first response entries=%d restored=%d errors=%d",
                  len(entries), issues["store_restored"], issues["store_errors"])
    return entries, snapshots, issues
