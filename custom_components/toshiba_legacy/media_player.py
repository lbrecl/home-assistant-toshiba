"""Media player for local Toshiba IPC v2 TVs."""

from homeassistant.exceptions import HomeAssistantError

from .api import InvalidAuth, ToshibaError

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from .entity import ToshibaEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ToshibaMediaPlayer(entry.runtime_data)])


SOURCES = {
    "HDMI 1 - TV": "HDMI_1",
    "HDMI 2 - Apple TV": "HDMI_2",
    "HDMI 3 - Jeux": "HDMI_3",
    "HDMI 4 - ChromeCast": "HDMI_4",
}


class ToshibaMediaPlayer(ToshibaEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_STEP
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
    def source_list(self):
        return list(SOURCES)

    @property
    def source(self):
        current = self.coordinator.data.get("external_input")
        return next((name for name, code in SOURCES.items() if code == current), current)

    async def async_select_source(self, source):
        if source not in SOURCES:
            raise HomeAssistantError(f"Unsupported Toshiba input: {source}")
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.select_input, SOURCES[source]
            )
        except InvalidAuth as err:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError("TV authentication failed; pair it again") from err
        except ToshibaError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

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
