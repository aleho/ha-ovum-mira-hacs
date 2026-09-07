"""Config flow for Ovum Mira integration."""

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

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=502): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=1,
                    max=65535,
                )
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_WPM_UNIT_ID, default=DEFAULT_WPM_UNIT_ID): vol.All(
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
        vol.Required(CONF_LICENSE_LEVEL, default="1"): vol.All(
            SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="license_level",
                    options=["1", "2", "3"],
                )
            ),
            vol.Coerce(int),
        ),
    }
)


class OvumConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ovum Mira."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up Modbus connection (host, port), set WPM ID, probe connectivity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO implement support for multiple WPM units
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
            step_id="user", data_schema=STEP_USER, errors=errors
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
