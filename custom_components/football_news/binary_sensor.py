"""Data availability signal for troubleshooting."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, VERSION, LEAGUES


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]["coordinator"]
    async_add_entities([FootballNewsConnected(coordinator, entry)])


class FootballNewsConnected(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "source_connected"
    _attr_icon = "mdi:cloud-check-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_source_connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Football News · {LEAGUES.get(coordinator.provider.league, coordinator.provider.league)}",
            manufacturer="Football News community", model="Football feed", sw_version=VERSION,
        )

    @property
    def available(self):
        # This entity is a diagnostic of ESPN, not a transport to ESPN.
        # It must remain visible when the provider is down.
        return True

    @property
    def is_on(self):
        if not self.coordinator._attempted_refresh:
            return None  # Unknown until the first background request finishes.
        data = self.coordinator.data or {}
        return bool(data.get("updated_at", {}).get("fixtures")) and not any(
            str(err).startswith("fixtures:") for err in self.coordinator._last_errors
        )

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "source": "ESPN",
            "league": self.coordinator.provider.league,
            "updated_at": data.get("updated_at", {}),
            "errors": self.coordinator._last_errors[:3],
        }
