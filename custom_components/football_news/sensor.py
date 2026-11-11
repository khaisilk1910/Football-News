"""Compact sensors: avoid stuffing news/fixture JSON into Recorder state attrs."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, VERSION, LEAGUES

DESCRIPTIONS = (
    SensorEntityDescription(key="live_matches", translation_key="live_matches", icon="mdi:soccer-field"),
    SensorEntityDescription(key="upcoming_matches", translation_key="upcoming_matches", icon="mdi:calendar-clock"),
    SensorEntityDescription(key="news_articles", translation_key="news_articles", icon="mdi:newspaper-variant-multiple"),
    SensorEntityDescription(key="next_kickoff", translation_key="next_kickoff", icon="mdi:calendar-start", device_class=SensorDeviceClass.TIMESTAMP),
    SensorEntityDescription(key="last_update", translation_key="last_update", icon="mdi:clock-check-outline", device_class=SensorDeviceClass.TIMESTAMP, entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]["coordinator"]
    async_add_entities([FootballNewsSensor(coordinator, entry, desc) for desc in DESCRIPTIONS])


class FootballNewsSensor(CoordinatorEntity, SensorEntity):
    """One entry = one league device and a few useful sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Football News · {LEAGUES.get(coordinator.provider.league, coordinator.provider.league)}",
            manufacturer="Football News community",
            model="Football feed", sw_version=VERSION,
        )

    @property
    def available(self):
        # Unknown on startup rather than pretending there are zero matches.
        data = self.coordinator.data or {}
        needed = "news" if self.entity_description.key == "news_articles" else "fixtures"
        return (self.coordinator.last_update_success
                and needed in data.get("updated_at", {})
                and not any(str(e).startswith(f"{needed}:") for e in data.get("errors", [])))

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        fixtures = data.get("fixtures", [])
        if self.entity_description.key == "live_matches":
            return sum(f.get("state") == "in" for f in fixtures)
        if self.entity_description.key == "upcoming_matches":
            return sum(f.get("state") == "pre" for f in fixtures)
        if self.entity_description.key == "news_articles":
            return len(data.get("news", []))
        if self.entity_description.key == "next_kickoff":
            future = []
            for fixture in fixtures:
                if fixture.get("state") != "pre" or not fixture.get("kickoff"):
                    continue
                try:
                    kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
                    if kickoff.tzinfo and kickoff > datetime.now(timezone.utc):
                        future.append(kickoff)
                except ValueError:
                    continue
            return min(future) if future else None
        if self.entity_description.key == "last_update":
            timestamp = data.get("updated_at", {}).get("fixtures")
            return datetime.fromisoformat(timestamp) if timestamp else None
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self.entity_description.key == "live_matches":
            return {"matches": [
                {"id": f["id"], "home": f["home"]["name"], "away": f["away"]["name"],
                 "score": f"{f['home']['score']} - {f['away']['score']}", "status": f["status"]}
                for f in data.get("fixtures", []) if f.get("state") == "in"
            ][:10], "source": data.get("source", "ESPN")}
        if self.entity_description.key == "last_update":
            return {"updated_at": data.get("updated_at", {}), "errors": data.get("errors", [])}
        return None
