"""Read-only pump and boiler enable states."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .entity_base import HargassnerEntity
from .capabilities import active_bool, cloud_ready


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, widget in (coordinator.data or {}).items():
        if not isinstance(widget, dict):
            continue
        for kind, value_key, translation in [('BUFFER','pump_active','buffer_pump'), ('HEATER','activated','heater_activated')]:
            if widget.get('widget_type') == kind and value_key in widget.get('values', {}):
                entities.append(HargassnerBinaryState(coordinator,key,value_key,translation,widget['widget_name']))
    async_add_entities(entities)


class HargassnerBinaryState(HargassnerEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, value_key, translation, name):
        super().__init__(coordinator,key,value_key,f'binary_{key}_{value_key}')
        self._attr_translation_key = translation
        self._attr_translation_placeholders = {'widget_name':name}

    @property
    def is_on(self):
        return active_bool(self._get_value())

    @property
    def available(self):
        return cloud_ready(self.coordinator) and self.is_on is not None
