"""Exercise the real Home Assistant flow manager with synthetic TV credentials."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.auth import auth_manager_from_config
from homeassistant.bootstrap import async_load_base_functionality
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.loader import async_setup as async_setup_loader

from custom_components.toshiba_legacy.api import CannotConnect
from tests.test_api import CHALLENGE

FEATURE = {"status": 0, "id": "synthetic-flow-tv", "model": "Test TV", "ipc_feature": ["PIN_Auth"]}


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    async_setup_loader(instance)
    instance.config_entries = config_entries.ConfigEntries(instance, {})
    await async_load_base_functionality(instance)
    instance.auth = await auth_manager_from_config(instance, [], [])
    await instance.config_entries.async_initialize()
    yield instance
    await instance.async_stop(force=True)


async def test_ui_pairing_retry_and_entry_creation(hass):
    with (
        patch("custom_components.toshiba_legacy.api.ToshibaClient.feature", return_value=FEATURE),
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.start_pairing",
            return_value=CHALLENGE,
        ) as start,
        patch("custom_components.toshiba_legacy.api.ToshibaClient.confirm_pairing") as confirm,
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.status",
            return_value={"status": 0, "power": "on"},
        ),
        patch("custom_components.toshiba_legacy.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            "toshiba_legacy", context={"source": "user"}
        )
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.0.2.10", "port": 8080}
        )
        assert result["step_id"] == "pin"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "0000"})
        assert result["errors"] == {"base": "invalid_pin"}
        confirm.assert_not_called()
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"restart": True}
        )
        assert start.call_count == 2
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "1234"})
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["password"] == "synthetic-password"
        assert result["data"]["host"] == "192.0.2.10"
        assert "pin" not in result["data"]
        await hass.async_block_till_done()
        duplicate = await hass.config_entries.flow.async_init(
            "toshiba_legacy", context={"source": "user"}, data={"host": "192.0.2.10", "port": 8080}
        )
        assert duplicate["reason"] == "already_configured"


async def test_ui_unreachable_and_unsupported(hass):
    with patch(
        "custom_components.toshiba_legacy.api.ToshibaClient.feature", side_effect=CannotConnect
    ):
        result = await hass.config_entries.flow.async_init(
            "toshiba_legacy", context={"source": "user"}, data={"host": "192.0.2.10", "port": 8080}
        )
        assert result["errors"] == {"base": "cannot_connect"}
    with patch(
        "custom_components.toshiba_legacy.api.ToshibaClient.feature", return_value={"id": "other"}
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.0.2.11", "port": 8080}
        )
        assert result["reason"] == "unsupported_tv"


async def test_real_entry_loads_all_entities(hass):
    with (
        patch("custom_components.toshiba_legacy.api.ToshibaClient.feature", return_value=FEATURE),
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.start_pairing",
            return_value=CHALLENGE,
        ),
        patch("custom_components.toshiba_legacy.api.ToshibaClient.confirm_pairing"),
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.status",
            return_value={"status": 0, "power": "on", "external_input": "HDMI_2"},
        ),
        patch("custom_components.toshiba_legacy.api.ToshibaClient.send_key") as send_key,
    ):
        flow = await hass.config_entries.flow.async_init(
            "toshiba_legacy", context={"source": "user"}, data={"host": "192.0.2.10", "port": 8080}
        )
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"pin": "1234"})
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state == config_entries.ConfigEntryState.LOADED
        assert len(hass.states.async_all("media_player")) == 1
        assert len(hass.states.async_all("remote")) == 1
        assert len(hass.states.async_all("button")) == 12
        player = hass.states.async_all("media_player")[0]
        assert player.state == "on"
        assert player.attributes["source"] == "HDMI_2"
        remote_id = hass.states.async_all("remote")[0].entity_id
        await hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": remote_id, "command": ["volume_up", "volume_down"], "delay_secs": 0},
            blocking=True,
        )
        assert [call.args[0] for call in send_key.call_args_list] == ["40bf1a", "40bf1e"]
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.fixture
async def paired_tv(hass):
    state = {"status": 0, "power": "off", "external_input": "HDMI_2"}

    def toggle(key):
        assert key == "40bf12"
        state["power"] = "off" if state["power"] == "on" else "on"

    with (
        patch("custom_components.toshiba_legacy.api.ToshibaClient.feature", return_value=FEATURE),
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.start_pairing",
            return_value=CHALLENGE,
        ),
        patch("custom_components.toshiba_legacy.api.ToshibaClient.confirm_pairing"),
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.status",
            side_effect=lambda: dict(state),
        ) as status,
        patch(
            "custom_components.toshiba_legacy.api.ToshibaClient.send_key", side_effect=toggle
        ) as send_key,
    ):
        flow = await hass.config_entries.flow.async_init(
            "toshiba_legacy", context={"source": "user"}, data={"host": "192.0.2.10", "port": 8080}
        )
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"pin": "1234"})
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state == config_entries.ConfigEntryState.LOADED
        yield hass, state, status, send_key
        await hass.config_entries.async_unload(entry.entry_id)


async def test_explicit_power_is_idempotent_across_entities(paired_tv):
    hass, state, status, send_key = paired_tv
    player = hass.states.async_all("media_player")[0].entity_id
    remote = hass.states.async_all("remote")[0].entity_id
    from homeassistant.components.media_player import MediaPlayerEntityFeature

    assert (
        hass.states.get(player).attributes["supported_features"] & MediaPlayerEntityFeature.TURN_ON
    )
    for domain, entity in [("media_player", player), ("remote", remote)]:
        await hass.services.async_call(domain, "turn_on", {"entity_id": entity}, blocking=True)
        assert state["power"] == "on"
    assert send_key.call_count == 1
    for domain, entity in [("remote", remote), ("media_player", player)]:
        await hass.services.async_call(domain, "turn_off", {"entity_id": entity}, blocking=True)
        assert state["power"] == "off"
    assert send_key.call_count == 2
    assert status.call_count >= 5


async def test_concurrent_power_on_never_toggles_back_off(paired_tv):
    import asyncio

    hass, state, _, send_key = paired_tv
    player = hass.states.async_all("media_player")[0].entity_id
    remote = hass.states.async_all("remote")[0].entity_id
    await asyncio.gather(
        hass.services.async_call("media_player", "turn_on", {"entity_id": player}, blocking=True),
        hass.services.async_call("remote", "turn_on", {"entity_id": remote}, blocking=True),
    )
    assert state["power"] == "on"
    assert send_key.call_count == 1


async def test_power_refuses_to_toggle_on_stale_state(paired_tv):
    from homeassistant.exceptions import HomeAssistantError

    hass, state, status, send_key = paired_tv
    player = hass.states.async_all("media_player")[0].entity_id
    status.side_effect = CannotConnect("offline")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "media_player", "turn_on", {"entity_id": player}, blocking=True
        )
    send_key.assert_not_called()
    assert state["power"] == "off"
