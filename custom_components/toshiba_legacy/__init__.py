"""Toshiba Legacy TV integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InvalidAuth, ToshibaClient, ToshibaError
from .const import DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)


class ToshibaCoordinator(DataUpdateCoordinator[dict]):
    """Read real state without assuming that an unreachable TV is off."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: ToshibaClient):
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=15)
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self.api.status)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Pair the TV again") from err
        except ToshibaError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    api = ToshibaClient(
        entry.data["host"], entry.data["port"], entry.data["username"], entry.data["password"]
    )
    coordinator = ToshibaCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
