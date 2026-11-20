"""Compact sensors: avoid stuffing news/fixture JSON into Recorder state attrs."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import Event, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, VERSION, LEAGUES
from .voice_schedule import schedule_next_round

DESCRIPTIONS = (
    SensorEntityDescription(key="live_matches", translation_key="live_matches", icon="mdi:soccer-field"),
    SensorEntityDescription(key="upcoming_matches", translation_key="upcoming_matches", icon="mdi:calendar-clock"),
    SensorEntityDescription(key="schedule_next_30_days", translation_key="schedule_next_30_days", icon="mdi:calendar-month"),
    SensorEntityDescription(key="news_articles", translation_key="news_articles", icon="mdi:newspaper-variant-multiple"),
    SensorEntityDescription(key="favorite_clubs", translation_key="favorite_clubs", icon="mdi:star-circle"),
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
        self._league = coordinator.provider.league
        self._league_name = LEAGUES.get(self._league, self._league)
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Football News · {LEAGUES.get(coordinator.provider.league, coordinator.provider.league)}",
            manufacturer="Football News community",
            model="Football feed", sw_version=VERSION,
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.entity_description.key == "favorite_clubs":
            self.async_on_remove(self.hass.bus.async_listen(
                f"{DOMAIN}_preferences_updated", self._async_preferences_updated
            ))

    @callback
    def _async_preferences_updated(self, event: Event) -> None:
        """Update the favourite-club sensor on Home Assistant's event loop.

        Bus listeners without @callback run in an executor thread on current HA;
        async_write_ha_state must never be called from that thread.
        """
        self.async_write_ha_state()

    def _fixtures(self):
        """Only use this coordinator's own league, even with mixed cache rows."""
        return [row for row in (self.coordinator.data or {}).get("fixtures", [])
                if isinstance(row, dict) and row.get("league", self._league) == self._league]

    def _schedule(self):
        tz = getattr(getattr(self.hass, "config", None), "time_zone", "UTC")
        return schedule_next_round(self._fixtures(), self._league, self._league_name, tz)

    @property
    def available(self):
        # Unknown on startup rather than pretending there are zero matches.
        if self.entity_description.key == "favorite_clubs":
            return self.hass.data[DOMAIN]["preferences"]._loaded
        data = self.coordinator.data or {}
        # A saved future calendar is still useful for voice while ESPN is down.
        # Historical Live states, unlike upcoming fixtures, are NOT trusted.
        if self.entity_description.key in ("upcoming_matches", "next_kickoff", "schedule_next_30_days"):
            return bool(data.get("updated_at", {}).get("fixtures"))
        needed = ("news" if self.entity_description.key == "news_articles"
                  else "any" if self.entity_description.key == "last_update" else "fixtures")
        if needed == "any":
            return bool(data.get("updated_at"))
        # Persisted counts are historic, not current HA live/news sensor data.
        restored = data.get("cache_info", {}).get("restored_datasets", [])
        if ((needed == "fixtures" and self.entity_description.key == "live_matches" and "fixtures" in restored)
                or (needed == "news" and "news" in restored)):
            return False
        return (bool(data.get("updated_at", {}).get(needed))
                and not any(str(e).startswith(f"{needed}:") for e in data.get("errors", [])))

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        fixtures = self._fixtures()
        if self.entity_description.key == "schedule_next_30_days":
            return self._schedule()["total_matches"]
        if self.entity_description.key == "live_matches":
            return sum(f.get("state") == "in" for f in fixtures)
        if self.entity_description.key == "upcoming_matches":
            return sum(f.get("state") == "pre" for f in fixtures)
        if self.entity_description.key == "news_articles":
            return len(data.get("news", []))
        if self.entity_description.key == "favorite_clubs":
            return sum(club.get("league") == self._league
                       for club in self.hass.data[DOMAIN]["preferences"]._data["clubs"])
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
            timestamps = list(data.get("updated_at", {}).values())
            return max(datetime.fromisoformat(value) for value in timestamps) if timestamps else None
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self.entity_description.key == "schedule_next_30_days":
            return {**self._schedule(),
                    "from_cache": "fixtures" in data.get("cache_info", {}).get("restored_datasets", [])}
        if self.entity_description.key == "live_matches":
            return {"league_code": self._league, "league": self._league_name, "matches": [
                {"id": f["id"], "home": f["home"]["name"], "away": f["away"]["name"],
                 "score": f"{f['home']['score']} - {f['away']['score']}", "status": f["status"]}
                for f in self._fixtures() if f.get("state") == "in"
            ][:10], "source": data.get("source", "ESPN")}
        if self.entity_description.key == "last_update":
            return {"league_code": self._league, "league": self._league_name,
                    "updated_at": data.get("updated_at", {}), "errors": data.get("errors", []),
                    "cache_info": data.get("cache_info", {})}
        if self.entity_description.key in ("upcoming_matches", "next_kickoff", "news_articles"):
            feed = "news" if self.entity_description.key == "news_articles" else "fixtures"
            return {"league_code": self._league, "league": self._league_name,
                    "from_cache": feed in data.get("cache_info", {}).get("restored_datasets", [])}
        if self.entity_description.key == "favorite_clubs":
            clubs = [club for club in self.hass.data[DOMAIN]["preferences"]._data["clubs"]
                     if club.get("league") == self._league]
            return {"league_code": self._league, "league": self._league_name,
                    "clubs": [{"id": x.get("id"), "name": x.get("name")}
                              for x in clubs[:5]]}
        return None
