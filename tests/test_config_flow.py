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
