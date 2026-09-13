"""Read-only pellet counters, refill ledger and trend-based range."""
from datetime import date, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util
from .const import DOMAIN

# key, unit, device class, state class
SENSORS = [
    ('pellet_total', 'kg', None, SensorStateClass.TOTAL_INCREASING),
    ('pellet_stock', 'kg', None, SensorStateClass.MEASUREMENT),
    ('pellet_refill_total', 'kg', None, None),
    ('pellet_last_refill', None, SensorDeviceClass.DATE, None),
    ('pellet_last_refill_amount', 'kg', None, None),
    ('pellet_refill_history', None, None, None),
    ('pellet_daily_average', 'kg/d', None, SensorStateClass.MEASUREMENT),
    ('pellet_days_remaining', 'd', SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT),
    ('pellet_empty_date', None, SensorDeviceClass.DATE, None),
]


def history_entities(coordinator):
    return [PelletHistorySensor(coordinator, *description) for description in SENSORS]


class PelletHistorySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, key, unit, device_class, state_class):
        self.history = coordinator.pellet_history
        self.key = key
        self._attr_translation_key = key
        suffix = self.history.entry.options.get('pellet_consumption_entity', 'none') if key == 'pellet_total' else ''
        self._attr_unique_id = f'{DOMAIN}_{coordinator.installation_id}_{key}_{suffix}'
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.installation_id)}, name=coordinator.installation_name, manufacturer='Hargassner', model='Touch Tronic')

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.history.listen(self.async_write_ha_state))

    @property
    def native_value(self):
        h = self.history
        records = h.ledger.refills
        now = dt_util.utcnow()
        rate, days = h.ledger.forecast(now.timestamp(), h.stock)
        if self.key == 'pellet_total': return h.counter
        if self.key == 'pellet_stock': return h.stock
        if self.key == 'pellet_refill_total': return sum(r['quantity_kg'] for r in records)
        if self.key == 'pellet_refill_history': return len(records)
        if self.key == 'pellet_last_refill': return date.fromisoformat(records[-1]['date']) if records else None
        if self.key == 'pellet_last_refill_amount': return records[-1]['quantity_kg'] if records else None
        if h.counter is None: return None
        if self.key == 'pellet_daily_average': return rate
        if self.key == 'pellet_days_remaining': return days
        if self.key == 'pellet_empty_date' and days is not None and days <= 3650:
            return dt_util.now().date() + timedelta(days=int(days))
        return None

    @property
    def extra_state_attributes(self):
        if self.key == 'pellet_refill_history':
            return {'records': self.history.ledger.refills[-50:], 'display_limit': 50, 'installation_id': str(self.history.coordinator.installation_id)}
        if self.key in ('pellet_daily_average','pellet_days_remaining','pellet_empty_date'):
            return {'window_days': 14, 'minimum_history_days': 3, 'method': 'recent_consumption_trend', 'weather_adjusted': False}
        return None
