"""Pellet history storage, source sampling and manual refill services."""
from datetime import timedelta
import asyncio
import copy
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_PELLET_CONSUMPTION_ENTITY
from .energy import pellet_energy_kwh
from .pellet_ledger import PelletLedger, nonnegative

STOCK_SOURCE = 'pellet_stock_entity'


class PelletHistory:
    def __init__(self, hass, entry, coordinator):
        self.hass, self.entry, self.coordinator = hass, entry, coordinator
        self.store = Store(hass, 1, f'{DOMAIN}_pellets_{entry.entry_id}')
        self.ledger = PelletLedger()
        self.listeners = set()
        self.lock = asyncio.Lock()
        self.counter = None
        self.stock = None

    async def setup(self):
        self.ledger = PelletLedger(await self.store.async_load())
        sources = [self.entry.options.get(CONF_PELLET_CONSUMPTION_ENTITY), self.entry.options.get(STOCK_SOURCE)]
        sources = [s for s in sources if s]
        if sources:
            self.entry.async_on_unload(async_track_state_change_event(self.hass, sources, self.update))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.update, timedelta(hours=1)))
        self.entry.async_on_unload(self.coordinator.async_add_listener(self.update))
        self.update()

    @callback
    def update(self, event=None):
        source_id = self.entry.options.get(CONF_PELLET_CONSUMPTION_ENTITY)
        source = self.hass.states.get(source_id) if source_id else None
        self.counter = None
        if source:
            self.counter = pellet_energy_kwh(source.state, source.attributes.get('unit_of_measurement'), source.attributes.get('state_class'), 1)
        stock_id = self.entry.options.get(STOCK_SOURCE)
        self.stock = None
        if stock_id:
            state = self.hass.states.get(stock_id)
            if state and state.attributes.get('unit_of_measurement') == 'kg':
                self.stock = nonnegative(state.state)
        elif self.coordinator.last_update_success and (self.coordinator.data or {}).get('_online') is True:
            stocks = [nonnegative(w.get('values', {}).get('fuel_stock')) for w in self.coordinator.data.values() if isinstance(w, dict) and w.get('widget_type') == 'HEATER' and 'fuel_stock' in w.get('values', {})]
            if len(stocks) == 1:
                self.stock = stocks[0]
        if self.counter is not None and self.ledger.sample(dt_util.utcnow().timestamp(), self.counter, source_id):
            self.store.async_delay_save(self.ledger.dump, 5)
        for listener in tuple(self.listeners):
            listener()

    def listen(self, listener):
        self.listeners.add(listener)
        return lambda: self.listeners.discard(listener)

    async def edit_refill(self, data, remove=False):
        async with self.lock:
            old = copy.deepcopy(self.ledger.refills)
            try:
                if remove:
                    self.ledger.remove_refill(data['record_id'])
                else:
                    self.ledger.record_refill(data['date'], data['quantity_kg'], dt_util.now().date(), data.get('note', ''))
                await self.store.async_save(self.ledger.dump())
            except Exception:
                self.ledger.refills = old
                raise
            self.update()


async def setup_history(hass, entry, coordinator):
    history = PelletHistory(hass, entry, coordinator)
    coordinator.pellet_history = history
    await history.setup()
    async def handle(call):
        candidates = [getattr(c, 'pellet_history', None) for c in hass.data.get(DOMAIN, {}).values()]
        candidates = [h for h in candidates if h is not None and str(h.coordinator.installation_id) == call.data['installation_id']]
        if len(candidates) != 1:
            raise HomeAssistantError('Anlage nicht eindeutig gefunden.')
        try:
            await candidates[0].edit_refill(call.data, call.service == 'remove_pellet_refill')
        except (ValueError, OSError) as err:
            raise HomeAssistantError(str(err)) from err
    schemas = {
        'record_pellet_refill': vol.Schema({vol.Required('installation_id'): cv.string, vol.Required('date'): cv.string, vol.Required('quantity_kg'): vol.Coerce(float), vol.Optional('note', default=''): cv.string}),
        'remove_pellet_refill': vol.Schema({vol.Required('installation_id'): cv.string, vol.Required('record_id'): cv.string}),
    }
    for service, schema in schemas.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handle, schema=schema)
