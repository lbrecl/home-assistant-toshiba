"""Pair a Toshiba TV directly from Home Assistant's user interface."""

from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from .api import (
    CannotConnect,
    InvalidAuth,
    InvalidPin,
    ToshibaClient,
    ToshibaError,
    decrypt_password,
    normalize_host,
)
from .const import DEFAULT_PORT, DOMAIN


class ToshibaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._host = ""
        self._port = DEFAULT_PORT
        self._feature = {}
        self._challenge = {}
        self._username = "-".join(f"{b:02X}" for b in (b"\x02" + uuid.uuid4().bytes[:5]))
        self._api = None

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self._host = normalize_host(user_input[CONF_HOST])
                self._port = user_input[CONF_PORT]
                self._api = ToshibaClient(self._host, self._port)
                self._feature = await self.hass.async_add_executor_job(self._api.feature)
                if "PIN_Auth" not in self._feature.get("ipc_feature", []) or not self._feature.get(
                    "id"
                ):
                    return self.async_abort(reason="unsupported_tv")
                await self.async_set_unique_id(self._feature["id"])
                self._abort_if_unique_id_configured()
                await self._async_start_pairing()
            except ValueError:
                errors["host"] = "invalid_host"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ToshibaError:
                errors["base"] = "pairing_failed"
            else:
                return await self.async_step_pin()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Required(CONF_PORT, default=self._port): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_start_pairing(self):
        self._challenge = await self.hass.async_add_executor_job(
            self._api.start_pairing, self._username
        )

    async def async_step_reauth(self, entry_data):
        entry = self._get_reauth_entry()
        self._host, self._port = entry_data[CONF_HOST], entry_data[CONF_PORT]
        self._feature = {
            "id": entry.unique_id,
            "model": entry_data.get("model"),
            "dtv_version": entry_data.get("firmware"),
        }
        self._api = ToshibaClient(self._host, self._port)
        # Go through a confirmation form before displaying a new PIN on the TV.
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                feature = await self.hass.async_add_executor_job(self._api.feature)
                if feature.get("id") != self._feature["id"]:
                    return self.async_abort(reason="wrong_tv")
                await self._async_start_pairing()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ToshibaError:
                errors["base"] = "pairing_failed"
            else:
                return await self.async_step_pin()
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({}), errors=errors
        )

    async def async_step_pin(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                if user_input.get("restart", False):
                    await self._async_start_pairing()
                else:
                    password = await self.hass.async_add_executor_job(
                        decrypt_password, user_input["pin"].strip(), self._challenge
                    )
                    api = ToshibaClient(self._host, self._port, self._username, password)
                    await self.hass.async_add_executor_job(api.confirm_pairing)
                    await self.hass.async_add_executor_job(api.status)
                    data = {
                        "host": self._host,
                        "port": self._port,
                        "username": self._username,
                        "password": password,
                        "model": self._feature.get("model"),
                        "firmware": self._feature.get("dtv_version"),
                    }
                    if self.source == config_entries.SOURCE_REAUTH:
                        return self.async_update_reload_and_abort(
                            self._get_reauth_entry(), data_updates=data
                        )
                    return self.async_create_entry(
                        title=f"Toshiba {self._feature.get('model', 'TV')}", data=data
                    )
            except InvalidPin, InvalidAuth:
                errors["base"] = "invalid_pin"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ToshibaError:
                errors["base"] = "pairing_failed"
        return self.async_show_form(
            step_id="pin",
            data_schema=vol.Schema(
                {
                    vol.Optional("pin", default=""): str,
                    vol.Optional("restart", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"host": self._host},
        )
