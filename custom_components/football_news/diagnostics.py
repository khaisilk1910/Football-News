"""Safe diagnostics that never export user Zalo IDs or message contents."""
from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    runtime = hass.data.get(DOMAIN, {}).get("entries", {}).get(entry.entry_id)
    data = (runtime["coordinator"].data or {}) if runtime else {}
    registry = hass.data.get(DOMAIN, {}).get("league_registry")
    stored_entries = []
    if registry is not None:
        try:
            # Entry IDs identify user configuration; export only league codes.
            stored_entries = [item.data["league"] for item in await registry.fallback_entries()]
        except Exception:
            stored_entries = []
    return {
        "integration_version": VERSION,
        "football_data_source": "ESPN",
        "persistence": {
            "football_data": "Home Assistant Store per config entry",
            "favourites": "Home Assistant Store shared by users",
            "appearance_navigation": "Home Assistant Store per authenticated user",
            "browser_local_data_cache": False,
        },
        "league": entry.data.get("league"),
        "ha_registry": {
            "native_entries": len(hass.config_entries.async_entries(DOMAIN)),
            "saved_league_codes": stored_entries,
            "runtime_ready": bool(runtime),
        },
        "notifications_enabled": bool(entry.options.get("zalo_enabled")),
        "alert_types": {k: bool(entry.options.get(k, False)) for k in
                        ("schedule_alerts", "kickoff_alerts", "goal_alerts", "result_alerts", "news_alerts")},
        "zalo_action_available": hass.services.has_service("zalo_bot", "send_message"),
        "dataset_counts": {key: len(data.get(key, [])) for key in ("fixtures", "standings", "news")},
        "last_successful_updates": data.get("updated_at", {}),
        "disk_cache": data.get("cache_info", {}),
        "adaptive_refresh": data.get("refresh_policy", {
            "mode": "startup", "seconds": 300, "focused_days": []}),
        "live_refresh_seconds_setting": entry.options.get("live_refresh_seconds", 20),
        "errors": [str(x)[:200] for x in (runtime["coordinator"]._last_errors if runtime else [])][:3],
    }
