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
    if not entries:
        # This is a real Store-first read: do not wait for async_setup_entry.
        # Both fallback sources use HA-owned disk storage, never ESPN.
        async def registry_entries():
            return await registry.fallback_entries() if registry else []

        async def recovered_snapshots():
            return await recovery.async_snapshots() if recovery else []

        try:
            found = await asyncio.wait_for(asyncio.gather(
                registry_entries(), recovered_snapshots(), return_exceptions=True), timeout=8)
        except asyncio.TimeoutError:
            found = [[], []]
            issues["store_errors"] += 1
            _LOGGER.warning("Football News HA Store league index timed out on first view")
        indexed, recovered = found
        if isinstance(indexed, BaseException):
            _LOGGER.warning("Football News saved league index read failed: %s", type(indexed).__name__)
            indexed = []
            issues["store_errors"] += 1
        if isinstance(recovered, BaseException):
            _LOGGER.warning("Football News saved cache discovery failed: %s", type(recovered).__name__)
            recovered = []
            issues["store_errors"] += 1
        for ent in indexed:
            if ent.entry_id not in known_ids:
                entries.append(ent)
                known_ids.add(ent.entry_id)
                issues["registry_fallback"] = True
        for ent, _ in recovered:
            if ent.entry_id not in known_ids:
                entries.append(ent)
                known_ids.add(ent.entry_id)
                issues["recovery_fallback"] = True
        recovery_cache = {ent.entry_id: snapshot for ent, snapshot in recovered if snapshot}
    else:
        recovery_cache = {}

    cold = state.get("cold_cache")
    snapshots = dict(recovery_cache)
    if entries and cold is not None:
        async def read_one(ent):
            try:
                # Read HA Store, even if RAM is populated. Only a very short
                # single-flight window prevents redundant concurrent disk I/O.
                return ent.entry_id, await asyncio.wait_for(
                    asyncio.shield(cold.async_entry_snapshot(ent, force=True)), timeout=7)
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

    # A re-created config entry has a new file key. Scan old *validated* HA
    # cache files only if the per-entry Store has no usable snapshots.
    if entries and not any(snapshots.values()) and recovery is not None:
        try:
            found = await asyncio.wait_for(recovery.async_snapshots(), timeout=7)
            by_code = {ent.data.get("league"): snapshot for ent, snapshot in found if snapshot}
            for ent in entries:
                old = by_code.get(ent.data.get("league"))
                if old and not snapshots.get(ent.entry_id):
                    snapshots[ent.entry_id] = old
                    issues["recovery_fallback"] = True
        except Exception as err:
            issues["store_errors"] += 1
            _LOGGER.warning("Football News saved cache scan unavailable: %s", type(err).__name__)
    issues["store_restored"] = sum(bool(snapshots.get(ent.entry_id)) for ent in entries)
    _LOGGER.debug("Football News HA Store-first response entries=%d restored=%d errors=%d",
                  len(entries), issues["store_restored"], issues["store_errors"])
    return entries, snapshots, issues
