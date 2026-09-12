"""Energy sensor using an explicitly selected cumulative kg sensor."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, PELLET_ENERGY_KWH_PER_KG
from .energy import pellet_energy_kwh


class PelletEnergySensor(SensorEntity):
    """Calculated fuel input energy, not measured delivered heat.

    The source is part of the unique ID so changing meters cannot merge unrelated
    cumulative series. The fixed conversion factor is intentionally not a mutable
    option, which would retroactively rescale a lifetime counter.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "pellet_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 1
    _attr_should_poll = False
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator, source_entity_id: str):
        self._source_entity_id = source_entity_id
        self._attr_unique_id = f"{DOMAIN}_{coordinator.installation_id}_pellet_energy_{source_entity_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.installation_id)},
            name=coordinator.installation_name,
            manufacturer="Hargassner",
            model="Touch Tronic",
        )
        self._attr_extra_state_attributes = {
            "source_entity": source_entity_id,
            "energy_content_kwh_per_kg": PELLET_ENERGY_KWH_PER_KG,
        }
        self._attr_available = False
        self._attr_native_value = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_track_state_change_event(
            self.hass, [self._source_entity_id], self._source_changed,
        ))
        self._read_source()

    @callback
    def _source_changed(self, event):
        self._read_source()
        self.async_write_ha_state()

    @callback
    def _read_source(self):
        source = self.hass.states.get(self._source_entity_id)
        value = None
        if source is not None:
            value = pellet_energy_kwh(
                source.state,
                source.attributes.get("unit_of_measurement"),
                source.attributes.get("state_class"),
                PELLET_ENERGY_KWH_PER_KG,
            )
        self._attr_native_value = value
        self._attr_available = value is not None
