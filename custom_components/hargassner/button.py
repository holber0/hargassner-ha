"""One-shot actions offered by the heater/buffer widgets."""
from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity_base import HargassnerEntity
from .capabilities import cloud_ready, enabled_resource

ACTIONS = {'HEATER': ('start_heating', 'stop_heating', 'start_ignition'), 'BUFFER': ('force_charging',)}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, widget in (coordinator.data or {}).items():
        if not isinstance(widget, dict):
            continue
        for action in ACTIONS.get(widget.get('widget_type'), ()):
            metadata = widget.get('actions', {}).get(action)
            if isinstance(metadata, dict) and metadata.get('resource'):
                if action == 'force_charging' and 'render_force_charging' in widget.get('values', {}):
                    continue  # Portal does not expose a force-charge control in this case.
                entities.append(HargassnerAction(coordinator, key, action, widget['widget_name']))
    async_add_entities(entities)


class HargassnerAction(HargassnerEntity, ButtonEntity):
    def __init__(self, coordinator, key, action, name):
        super().__init__(coordinator, key, action, f'action_{key}_{action}')
        self._attr_translation_key = action
        self._attr_translation_placeholders = {'widget_name': name}
        self._busy = False

    def _action_resource(self):
        widget = self._get_widget() or {}
        if self._param_key == 'force_charging' and 'render_force_charging' in widget.get('values', {}):
            return None
        return enabled_resource(widget.get('actions', {}).get(self._param_key))

    @property
    def available(self):
        return not self._busy and cloud_ready(self.coordinator) and bool(self._action_resource())

    async def async_press(self):
        if self._busy:
            raise HomeAssistantError('Aktion läuft bereits.')
        self._busy = True
        try:
            await self.coordinator.async_request_refresh()
            resource = self._action_resource()
            if not cloud_ready(self.coordinator) or not resource:
                raise HomeAssistantError('Aktion derzeit gesperrt oder Anlage nicht erreichbar.')
            if not await self.coordinator.async_post_action(resource):
                raise HomeAssistantError('Aktion konnte nicht ausgeführt werden.')
        finally:
            self._busy = False
