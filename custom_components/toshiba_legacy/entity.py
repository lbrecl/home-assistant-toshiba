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
