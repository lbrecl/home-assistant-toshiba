"""Media player for local Toshiba IPC v2 TVs."""

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from .entity import ToshibaEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ToshibaMediaPlayer(entry.runtime_data)])


class ToshibaMediaPlayer(ToshibaEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator):
        super().__init__(coordinator, "media_player")

    @property
    def state(self):
        return (
            MediaPlayerState.ON
            if self.coordinator.data.get("power") == "on"
            else MediaPlayerState.OFF
        )

    @property
    def source(self):
        return self.coordinator.data.get("external_input") or self.coordinator.data.get(
            "foreground_dtvapp"
        )

    @property
    def extra_state_attributes(self):
        return {"channel": self.coordinator.data.get("channel"), "network_wake_verified": False}

    async def async_volume_up(self):
        await self.async_key("volume_up")

    async def async_volume_down(self):
        await self.async_key("volume_down")

    async def async_turn_off(self):
        # Refresh first: a toggle must not wake a TV whose state changed meanwhile.
        await self.coordinator.async_refresh()
        if not self.coordinator.last_update_success:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Cannot confirm TV state before switching off")
        if self.coordinator.data.get("power") == "on":
            await self.async_key("power")
            await self.coordinator.async_request_refresh()
