"""Named remote commands for Toshiba televisions."""

import asyncio

from homeassistant.components.remote import RemoteEntity
from homeassistant.exceptions import HomeAssistantError

from .const import KEYS
from .entity import ToshibaEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ToshibaRemote(entry.runtime_data)])


class ToshibaRemote(ToshibaEntity, RemoteEntity):
    _attr_translation_key = "remote"

    def __init__(self, coordinator):
        super().__init__(coordinator, "remote")

    @property
    def is_on(self):
        return self.coordinator.data.get("power") == "on"

    async def async_send_command(self, command, **kwargs):
        commands = [command] if isinstance(command, str) else list(command)
        if any(key not in KEYS for key in commands):
            raise HomeAssistantError("Unknown command; see the integration README")
        repeats = int(kwargs.get("num_repeats", 1))
        delay = float(kwargs.get("delay_secs", 0.3))
        if not 1 <= repeats <= 10 or not 0 <= delay <= 5 or len(commands) > 30:
            raise HomeAssistantError("Use at most 30 commands, 10 repeats, and a 0–5 s delay")
        if kwargs.get("hold_secs", 0):
            raise HomeAssistantError("Holding a key is not supported")
        for _ in range(repeats):
            for key in commands:
                await self.async_key(key)
                await asyncio.sleep(delay)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self.async_set_power("on")

    async def async_turn_off(self, **kwargs):
        await self.async_set_power("off")
