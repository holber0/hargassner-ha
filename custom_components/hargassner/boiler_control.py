"""Explicit boiler programs and enable parameter advertised by the API."""
from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from .entity_base import HargassnerEntity
from .capabilities import active_bool, allowed_programs, cloud_ready, enabled_resource


def heater_widgets(coordinator):
    for key, widget in (coordinator.data or {}).items():
        if isinstance(widget, dict) and widget.get('widget_type') == 'HEATER':
            yield key, widget


def program_entities(coordinator):
    return [BoilerProgram(coordinator, key, widget['widget_name'])
            for key, widget in heater_widgets(coordinator)
            if allowed_programs(widget.get('parameters', {}).get('program'))
            and widget.get('parameters', {}).get('program', {}).get('resource')]


def activation_entities(coordinator):
    return [BoilerActivation(coordinator, key, widget['widget_name'])
            for key, widget in heater_widgets(coordinator)
            if isinstance(widget.get('parameters', {}).get('activated'), dict)
            and widget['parameters']['activated'].get('resource')]


class BoilerProgram(HargassnerEntity, SelectEntity):
    _attr_translation_key = 'heater_program'

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, 'program', f'boiler_program_{key}')
        self._attr_translation_placeholders = {'widget_name': name}

    @property
    def options(self):
        return allowed_programs(self._get_parameter())

    @property
    def current_option(self):
        parameter = self._get_parameter() or {}
        value = parameter.get('value')
        return value if value in self.options else None

    @property
    def available(self):
        return cloud_ready(self.coordinator) and bool(enabled_resource(self._get_parameter()))

    async def async_select_option(self, option):
        await self.coordinator.async_request_refresh()
        if not self.available or option not in self.options:
            raise HomeAssistantError('Kesselprogramm derzeit nicht verfügbar oder nicht freigegeben.')
        if not await self.coordinator.async_patch_value(enabled_resource(self._get_parameter()), option):
            raise HomeAssistantError('Kesselprogramm konnte nicht geändert werden.')


class BoilerActivation(HargassnerEntity, SwitchEntity):
    _attr_translation_key = 'heater_activation'

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, 'activated', f'boiler_activation_{key}')
        self._attr_translation_placeholders = {'widget_name': name}

    @property
    def is_on(self):
        return active_bool(self._get_value())

    @property
    def available(self):
        return cloud_ready(self.coordinator) and self.is_on is not None and bool(enabled_resource(self._get_parameter()))

    async def _set_activation(self, value):
        await self.coordinator.async_request_refresh()
        if not self.available:
            raise HomeAssistantError('Kesselfreigabe derzeit nicht verfügbar.')
        if not await self.coordinator.async_patch_value(enabled_resource(self._get_parameter()), value):
            raise HomeAssistantError('Kesselfreigabe konnte nicht geändert werden.')

    async def async_turn_on(self, **kwargs):
        await self._set_activation(1)

    async def async_turn_off(self, **kwargs):
        await self._set_activation(0)
