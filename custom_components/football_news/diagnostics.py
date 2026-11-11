"""Safe diagnostics that never export user Zalo IDs or message contents."""
from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    runtime = hass.data.get(DOMAIN, {}).get("entries", {}).get(entry.entry_id)
    data = (runtime["coordinator"].data or {}) if runtime else {}
    return {
        "integration_version": VERSION,
        "league": entry.data.get("league"),
        "notifications_enabled": bool(entry.options.get("zalo_enabled")),
        "alert_types": {k: bool(entry.options.get(k, False)) for k in
                        ("schedule_alerts", "kickoff_alerts", "result_alerts", "news_alerts")},
        "zalo_action_available": hass.services.has_service("zalo_bot", "send_message"),
        "dataset_counts": {key: len(data.get(key, [])) for key in ("fixtures", "standings", "news")},
        "last_successful_updates": data.get("updated_at", {}),
        "errors": [str(x)[:200] for x in data.get("errors", [])][:3],
    }
