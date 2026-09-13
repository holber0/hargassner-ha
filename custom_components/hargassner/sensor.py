"""Sensor entities for Hargassner."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity_base import HargassnerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HargassnerSensorDescription(SensorEntityDescription):
    """Describes a Hargassner sensor."""
    value_key: str = ""


# (widget_type_prefix, value_key, description)
SENSOR_DESCRIPTIONS: list[tuple[str, str, HargassnerSensorDescription]] = [
    # --- HEATER ---
    ("HEATER", "heater_temperature_current", HargassnerSensorDescription(
        key="heater_temp_current",
        translation_key="heater_temp_current",
        value_key="heater_temperature_current",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "heater_temperature_target", HargassnerSensorDescription(
        key="heater_temp_target",
        translation_key="heater_temp_target",
        value_key="heater_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "smoke_temperature", HargassnerSensorDescription(
        key="smoke_temperature",
        translation_key="smoke_temperature",
        value_key="smoke_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "outdoor_temperature", HargassnerSensorDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        value_key="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "outdoor_temperature_average", HargassnerSensorDescription(
        key="outdoor_temperature_average",
        translation_key="outdoor_temperature_average",
        value_key="outdoor_temperature_average",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "state", HargassnerSensorDescription(
        key="heater_state",
        translation_key="heater_state",
        value_key="state",
        icon="mdi:fire",
    )),
    ("HEATER", "program", HargassnerSensorDescription(
        key="heater_program",
        translation_key="heater_program",
        value_key="program",
        icon="mdi:calendar-clock",
    )),
    ("HEATER", "fuel_stock", HargassnerSensorDescription(
        key="fuel_stock",
        translation_key="fuel_stock",
        value_key="fuel_stock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kg",
        icon="mdi:sack",
    )),
    ("HEATER", "efficiency", HargassnerSensorDescription(
        key="efficiency",
        translation_key="efficiency",
        value_key="efficiency",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
    )),
    # --- HEATING CIRCUIT ---
    ("HEATING_CIRCUIT", "flow_temperature_current", HargassnerSensorDescription(
        key="flow_temp_current",
        translation_key="flow_temp_current",
        value_key="flow_temperature_current",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATING_CIRCUIT", "flow_temperature_target", HargassnerSensorDescription(
        key="flow_temp_target",
        translation_key="flow_temp_target",
        value_key="flow_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATING_CIRCUIT", "room_temperature_current", HargassnerSensorDescription(
        key="room_temp_current",
        translation_key="room_temp_current",
        value_key="room_temperature_current",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATING_CIRCUIT", "room_temperature_target", HargassnerSensorDescription(
        key="room_temp_target",
        translation_key="room_temp_target",
        value_key="room_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATING_CIRCUIT", "state", HargassnerSensorDescription(
        key="circuit_state",
        translation_key="circuit_state",
        value_key="state",
        icon="mdi:radiator",
    )),
    ("HEATING_CIRCUIT", "pump_active", HargassnerSensorDescription(
        key="pump_active",
        translation_key="pump_active",
        value_key="pump_active",
        icon="mdi:pump",
    )),
]


# Fields verified against the Hargassner portal Buffer and Heater widgets.
SENSOR_DESCRIPTIONS.extend([
    ("BUFFER", "buffer_temperature_top", HargassnerSensorDescription(
        key="buffer_temperature_top", translation_key="buffer_temperature_top", value_key="buffer_temperature_top",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("BUFFER", "buffer_temperature_center_top", HargassnerSensorDescription(
        key="buffer_temperature_center_top", translation_key="buffer_temperature_center_top", value_key="buffer_temperature_center_top",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("BUFFER", "buffer_temperature_center", HargassnerSensorDescription(
        key="buffer_temperature_center", translation_key="buffer_temperature_center", value_key="buffer_temperature_center",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("BUFFER", "buffer_temperature_center_bottom", HargassnerSensorDescription(
        key="buffer_temperature_center_bottom", translation_key="buffer_temperature_center_bottom", value_key="buffer_temperature_center_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("BUFFER", "buffer_temperature_bottom", HargassnerSensorDescription(
        key="buffer_temperature_bottom", translation_key="buffer_temperature_bottom", value_key="buffer_temperature_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("BUFFER", "buffer_charge", HargassnerSensorDescription(
        key="buffer_charge", translation_key="buffer_charge", value_key="buffer_charge",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=PERCENTAGE,
    )),
    ("BUFFER", "max_requirement", HargassnerSensorDescription(
        key="max_requirement", translation_key="max_requirement", value_key="max_requirement",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )),
    ("HEATER", "system_pressure", HargassnerSensorDescription(
        key="system_pressure", translation_key="system_pressure", value_key="system_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="bar",
    )),
])

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hargassner sensor entities."""
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[HargassnerSensorEntity] = []

    if not coordinator.data:
        return

    for widget_key, widget_data in coordinator.data.items():
        if not isinstance(widget_data, dict) or "widget_type" not in widget_data:
            continue

        widget_type = widget_data["widget_type"]
        widget_name = widget_data["widget_name"]
        values = widget_data.get("values", {})

        for prefix, value_key, description in SENSOR_DESCRIPTIONS:
            if not widget_type.startswith(prefix):
                continue
            if value_key not in values:
                continue

            entities.append(
                HargassnerSensorEntity(
                    coordinator=coordinator,
                    widget_key=widget_key,
                    param_key=value_key,
                    widget_name=widget_name,
                    description=description,
                )
            )

    # Optional energy sensor follows the local source, independently of cloud polling.
    from .energy_sensor import PelletEnergySensor
    from .const import CONF_PELLET_CONSUMPTION_ENTITY

    source = entry.options.get(CONF_PELLET_CONSUMPTION_ENTITY)
    if source:
        entities.append(PelletEnergySensor(coordinator, source))

    from .pellet_sensor import history_entities
    entities.extend(history_entities(coordinator))

    # Add online state sensor
    entities.append(HargassnerOnlineSensor(coordinator))
    async_add_entities(entities)


class HargassnerSensorEntity(HargassnerEntity, SensorEntity):
    """A sensor entity for a Hargassner parameter."""

    entity_description: HargassnerSensorDescription

    def __init__(
        self,
        coordinator: HargassnerCoordinator,
        widget_key: str,
        param_key: str,
        widget_name: str,
        description: HargassnerSensorDescription,
    ) -> None:
        super().__init__(
            coordinator,
            widget_key,
            param_key,
            f"{widget_key}_{description.key}",
        )
        self.entity_description = description
        if description.key in ("heater_state", "heater_program"):
            self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_translation_placeholders = {"widget_name": widget_name}

    @property
    def options(self):
        if self.entity_description.key in ("heater_state", "heater_program"):
            value = self._get_value()
            return [str(value)] if value is not None else []
        return None

    @property
    def native_value(self) -> Any:
        value = self._get_value()
        if self.entity_description.key in ("heater_state", "heater_program"):
            return str(value) if value is not None else None
        return value


class HargassnerOnlineSensor(HargassnerEntity, SensorEntity):
    """Sensor showing if the boiler is online."""

    def __init__(self, coordinator: HargassnerCoordinator) -> None:
        super().__init__(coordinator, "_online", "_online", "online_state")
        self._attr_translation_key = "online_state"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["En ligne", "Hors ligne", "Inconnu"]
        self._attr_icon = "mdi:cloud-check"

    @property
    def native_value(self) -> str:
        if self.coordinator.data:
            return "En ligne" if self.coordinator.data.get("_online", True) else "Hors ligne"
        return "Inconnu"

    @property
    def icon(self) -> str:
        if self.coordinator.data and not self.coordinator.data.get("_online", True):
            return "mdi:cloud-off-outline"
        return "mdi:cloud-check"
