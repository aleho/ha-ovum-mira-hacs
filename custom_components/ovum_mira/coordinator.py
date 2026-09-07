"""DataUpdateCoordinator that polls the Ovum Mira controller."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import ModbusError
from ovum_mira_modbus import (
    OvumLicense,
    OvumMira,
)

from .const import DOMAIN, SCAN_INTERVAL

type OvumConfigEntry = ConfigEntry[OvumCoordinator]


class OvumCoordinator(DataUpdateCoordinator[OvumMira]):
    """Refreshes Ovum Mira subsystems on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: OvumConfigEntry,
        device: OvumMira,
        license: OvumLicense,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self.license = license

    async def _async_update_data(self) -> OvumMira:
        """Fetch data from both units."""
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with Ovum Mira: {err}") from err

        return self.device
