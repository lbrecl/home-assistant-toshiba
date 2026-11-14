"""Shared TV entity helpers."""

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import InvalidAuth, ToshibaError
from .const import DOMAIN, KEYS


class ToshibaEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, suffix):
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.unique_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Toshiba",
            model=entry.data.get("model"),
            sw_version=entry.data.get("firmware"),
        )

    async def async_key(self, command):
        if command not in KEYS:
            raise HomeAssistantError(f"Unknown Toshiba command: {command}")
        try:
            await self.hass.async_add_executor_job(self.coordinator.api.send_key, KEYS[command])
        except InvalidAuth as err:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError("TV authentication failed; pair it again") from err
        except ToshibaError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_set_power(self, desired: str):
        """Turn on/off only from a freshly confirmed opposite state.

        The TV exposes a toggle key, so serialize explicit power requests across
        the media player and remote to prevent duplicate ON requests toggling OFF.
        """
        async with self.coordinator.power_lock:
            await self.coordinator.async_refresh()
            if not self.coordinator.last_update_success:
                raise HomeAssistantError(
                    "Cannot confirm TV power state. Enable TV Power On Control "
                    "(active standby) and check that the TV remains reachable."
                )
            current = self.coordinator.data.get("power")
            if current not in ("on", "off"):
                raise HomeAssistantError("The TV returned an unknown power state")
            if current == desired:
                return
            await self.async_key("power")
            await self.coordinator.async_refresh()
