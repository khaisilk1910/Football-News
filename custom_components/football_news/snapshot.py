"""Pure helpers for assembling frontend data from the HA config-entry registry.

An entry can exist in Settings > Devices & services before its runtime loads.
The dashboard must not mistake that state for zero configured leagues.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from .qualification import position_zone


def entry_state(entry) -> str:
    """Return a stable, non-sensitive HA config-entry status."""
    state = getattr(entry, "state", None)
    value = getattr(state, "value", state)
    return str(value).lower() if value is not None else "unknown"


def runtime_for_entry(entry, runtimes: dict):
    """Use the registered coordinator, or the config entry's runtime_data."""
    runtime = runtimes.get(entry.entry_id)
    if isinstance(runtime, dict) and runtime.get("coordinator") is not None:
        return runtime
    runtime = getattr(entry, "runtime_data", None)
    return runtime if isinstance(runtime, dict) and runtime.get("coordinator") is not None else None


def _newer_server_feed(server_stamp: object, disk_stamp: object) -> bool:
    """Only newer, timestamped coordinator feeds may supersede HA Store."""
    if not isinstance(server_stamp, str):
        return False
    if not isinstance(disk_stamp, str):
        return True
    try:
        server = datetime.fromisoformat(server_stamp.replace("Z", "+00:00"))
        disk = datetime.fromisoformat(disk_stamp.replace("Z", "+00:00"))
        return server.tzinfo is not None and disk.tzinfo is not None and server > disk
    except (ValueError, TypeError):
        return False


def competition_snapshot(config_entries, runtimes: dict, league_names: dict,
                         disk_fallbacks: dict | None = None) -> list[dict]:
    """Expose both loaded and not-yet-loaded entries without inventing scores."""
    result = []
    seen = set()
    for entry in config_entries:
        code = entry.data.get("league") if isinstance(entry.data, Mapping) else None
        if not code or code in seen:
            continue
        seen.add(code)
        runtime = runtime_for_entry(entry, runtimes)
        coordinator = runtime["coordinator"] if runtime else None
        snapshot = (getattr(coordinator, "data", None) if coordinator else None) or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        cached = (disk_fallbacks or {}).get(entry.entry_id) or {}
        if cached:
            # The shared HA Store is the first-view source of truth. Merge by
            # feed timestamp so an unhydrated or stale coordinator cannot hide
            # data already committed to HA storage. Newer ESPN data on the
            # server is still visible while its delayed Store write completes.
            restored = []
            combined = dict(snapshot)
            combined["updated_at"] = dict(snapshot.get("updated_at") or {})
            for name in ("fixtures", "standings", "news"):
                cached_rows = cached.get(name) or []
                if not cached_rows or name not in cached.get("updated_at", {}):
                    continue
                live_rows = combined.get(name) or []
                if live_rows and _newer_server_feed(
                        combined["updated_at"].get(name), cached["updated_at"].get(name)):
                    continue
                combined[name] = cached_rows
                combined["updated_at"][name] = cached["updated_at"][name]
                restored.append(name)
            if restored:
                existing = (snapshot.get("cache_info") or {}).get("restored_datasets", [])
                combined["cache_info"] = {"type": "disk",
                    "restored_datasets": sorted(set(existing) | set(restored))}
                snapshot = combined
        last_errors = getattr(coordinator, "_last_errors", []) if coordinator else []
        errors = snapshot.get("errors") or last_errors or []
        if not isinstance(errors, list):
            errors = [str(errors)]
        status = entry_state(entry)
        if not coordinator:
            errors = [f"Runtime chưa sẵn sàng (config entry: {status})", *errors]
        rankings = (snapshot.get("standings") or [])[:80]
        decorated = [{**row, "zone": position_zone(code, row.get("position"), len(rankings))}
                     for row in rankings if isinstance(row, dict)]
        result.append({
            "league_code": code,
            "name": league_names.get(code, code),
            "logo": snapshot.get("league_logo") or cached.get("league_logo") or "",
            "entry_id": entry.entry_id,
            "entry_state": status,
            "runtime_loaded": coordinator is not None,
            "fixtures": (snapshot.get("fixtures") or [])[:400],
            "standings": decorated,
            "news": (snapshot.get("news") or [])[:30],
            "updated_at": snapshot.get("updated_at") or {},
            "cache_info": snapshot.get("cache_info") or {},
            "errors": [str(e)[:220] for e in errors[:3]],
            "attempted": bool(getattr(coordinator, "_attempted_refresh", False)),
            # `ready` means at least one cached/upstream dataset exists, NOT
            # that the ESPN refresh has completed. Clients must check attempted
            # separately before exiting their initial hydration/retry loop.
            "ready": bool(snapshot.get("updated_at")) and any(
                snapshot.get(name) for name in ("fixtures", "standings", "news")
            ),
        })
    return result
