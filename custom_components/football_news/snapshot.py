"""Pure helpers for assembling frontend data from the HA config-entry registry.

An entry can exist in Settings > Devices & services before its runtime loads.
The dashboard must not mistake that state for zero configured leagues.
"""
from __future__ import annotations

from collections.abc import Mapping

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
            # A newly created runtime may have fixtures but no standings yet.
            # Restore each feed independently until its coordinator has a
            # successful timestamp, without replacing newer network data.
            restored = []
            combined = dict(snapshot)
            combined["updated_at"] = dict(snapshot.get("updated_at") or {})
            for name in ("fixtures", "standings", "news"):
                if name not in combined["updated_at"] and name in cached.get("updated_at", {}):
                    combined[name] = cached.get(name, [])
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
            "ready": bool(snapshot.get("updated_at")),
        })
    return result
