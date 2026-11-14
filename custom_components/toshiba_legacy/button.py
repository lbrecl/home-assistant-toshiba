"""Convenient remote buttons."""

from homeassistant.components.button import ButtonEntity

from .entity import ToshibaEntity

BUTTONS = {
    "power": "mdi:power",
    "mute": "mdi:volume-off",
    "input": "mdi:video-input-hdmi",
    "up": "mdi:arrow-up",
    "down": "mdi:arrow-down",
    "left": "mdi:arrow-left",
    "right": "mdi:arrow-right",
    "ok": "mdi:check",
    "back": "mdi:arrow-u-left-top",
    "menu": "mdi:menu",
    "exit": "mdi:close",
    "info": "mdi:information",
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [ToshibaButton(entry.runtime_data, key, icon) for key, icon in BUTTONS.items()]
    )


class ToshibaButton(ToshibaEntity, ButtonEntity):
    def __init__(self, coordinator, key, icon):
        super().__init__(coordinator, key)
        self._key = key
        self._attr_translation_key = key
        self._attr_icon = icon

    async def async_press(self):
        await self.async_key(self._key)
        await self.coordinator.async_request_refresh()
