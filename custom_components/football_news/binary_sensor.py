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
    def is_on(self):
        data = self.coordinator.data or {}
        return (self.coordinator.last_update_success and "fixtures" in data.get("updated_at", {})
                and not any(str(e).startswith("fixtures:") for e in data.get("errors", [])))
