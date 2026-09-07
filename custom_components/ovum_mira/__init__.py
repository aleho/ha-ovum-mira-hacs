"""Ovum Mira integration for Home Assistant

Custom integration using the ovum-mira-modbus library.
"""

from __future__ import annotations

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from modbus_connection import (
    ModbusTcpParams,
)
from ovum_mira_modbus import (
    DEFAULT_WPM_UNIT_ID,
    HSM_UNIT_ID,
    OvumLicense,
    OvumMira,
)

from .const import (
    CONF_LICENSE_LEVEL,
    CONF_WPM_UNIT_ID,
)
from .coordinator import OvumConfigEntry, OvumCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.WATER_HEATER,
]


async def async_setup_entry(hass: HomeAssistant, entry: OvumConfigEntry) -> bool:
    params = ModbusTcpParams(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )

    wpm_unit_id = entry.data.get(CONF_WPM_UNIT_ID, DEFAULT_WPM_UNIT_ID)

    wpm_unit = async_get_unit(
        hass=hass,
        entry=entry,
        params=params,
        unit_id=wpm_unit_id,
    )

    hsm_unit = async_get_unit(
        hass=hass,
        entry=entry,
        params=params,
        unit_id=HSM_UNIT_ID,
    )

    license = OvumLicense(int(entry.data[CONF_LICENSE_LEVEL]))

    device = OvumMira(
        license=license,
        wpm_unit=wpm_unit,
        hsm_unit=hsm_unit,
    )

    coordinator = OvumCoordinator(hass, entry, device, license)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OvumConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
