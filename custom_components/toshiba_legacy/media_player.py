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
        MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.TURN_ON
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
        return {
            "channel": self.coordinator.data.get("channel"),
            "wake_requires_active_standby": True,
        }

    async def async_volume_up(self):
        await self.async_key("volume_up")

    async def async_volume_down(self):
        await self.async_key("volume_down")

    async def async_turn_on(self):
        await self.async_set_power("on")

    async def async_turn_off(self):
        await self.async_set_power("off")
