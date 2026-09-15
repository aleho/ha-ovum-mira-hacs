"""Config flow for Ovum Mira integration."""
# TODO implement support for multiple WPM units?

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from modbus_connection import (
    ModbusError,
    ModbusTcpParams,
)
from ovum_mira_modbus import (
    DEFAULT_WPM_UNIT_ID,
    OvumMira,
)

from .const import (
    CONF_LICENSE_LEVEL,
    CONF_WPM_UNIT_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class OvumConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ovum Mira."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up Modbus connection (host, port), set WPM ID, probe connectivity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial_number = await self._async_probe(user_input)

            if not serial_number:
                errors[CONF_HOST] = "cannot_connect"

            else:
                await self.async_set_unique_id(serial_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Ovum Mira",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            serial_number = entry.unique_id

            if not serial_number:
                errors[CONF_HOST] = "cannot_connect"

            else:
                await self.async_set_unique_id(serial_number)
                self._abort_if_unique_id_mismatch()

                return self.async_update_reload_and_abort(
                    title="Ovum Mira",
                    entry=entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            errors=errors,
            data_schema=self._build_schema(
                host=entry.data[CONF_HOST],
                port=entry.data[CONF_PORT],
                wpm_unit_id=entry.data[CONF_WPM_UNIT_ID],
                license_level=entry.data[CONF_LICENSE_LEVEL],
            ),
        )

    async def _async_probe(self, data: dict[str, Any]) -> str | None:
        """Verify device connectivity, return the serial_number."""
        serial_number = None

        try:
            params = ModbusTcpParams(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
            )

            async with async_get_temporary_unit(
                self.hass,
                params,
                data[CONF_WPM_UNIT_ID],
            ) as unit:
                serial_number = await OvumMira.async_probe(unit)
        except (HomeAssistantError, ModbusError, OSError, ValueError) as e:
            _LOGGER.error("Error establishing Modbus TCP connection: %s", e)
            return None

        return (
            serial_number
            if serial_number is not None and len(serial_number) > 0
            else None
        )

    @staticmethod
    def _build_schema(
        host: str = "",
        port: int = 502,
        wpm_unit_id: int = DEFAULT_WPM_UNIT_ID,
        license_level: int = 1,
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=host): TextSelector(),
                vol.Required(CONF_PORT, default=port): vol.All(
                    NumberSelector(
                        NumberSelectorConfig(
                            mode=NumberSelectorMode.BOX,
                            min=1,
                            max=65535,
                        )
                    ),
                    vol.Coerce(int),
                ),
                vol.Required(CONF_WPM_UNIT_ID, default=wpm_unit_id): vol.All(
                    NumberSelector(
                        NumberSelectorConfig(
                            min=DEFAULT_WPM_UNIT_ID,
                            max=118,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Coerce(int),
                ),
                vol.Required(CONF_LICENSE_LEVEL, default=str(license_level)): vol.All(
                    SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="license_level",
                            options=["1", "2"],
                        )
                    ),
                    vol.Coerce(int),
                ),
            }
        )
