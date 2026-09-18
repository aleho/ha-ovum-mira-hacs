"""Base entity for Ovum Mira and helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Any, Self

from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ovum_mira_modbus import (
    OvumComponent,
    OvumLicense,
    OvumMira,
)

from .const import DOMAIN
from .coordinator import OvumConfigEntry, OvumCoordinator
from .enum import Component

_LOGGER = logging.getLogger(__name__)


def enum_options(enum: IntEnum | StrEnum) -> list[str]:
    return [e.name.lower() for e in enum]


class OvumEntityDescription(EntityDescription):
    component: Component
    attribute: str | None = None
    license: OvumLicense = OvumLicense.BASIC


class OvumEntity(CoordinatorEntity[OvumCoordinator]):
    """Common identity and device-info for Ovum Mira entities"""

    entity_description: OvumEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OvumCoordinator,
        description: OvumEntityDescription,
        **kwargs: Any,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        entry = coordinator.config_entry
        registry = device_registry.async_get(coordinator.hass)

        hsm_serial_number = entry.unique_id or "__no_serial_number__"

        hsm_device = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, hsm_serial_number)},
            manufacturer="Ovum",
            model="Mira",
            name="Ovum Mira",
            serial_number=hsm_serial_number,
            sw_version=self._device.hsm.version,
        )

        if description.component == Component.HEAT_PUMP:
            wpm_serial_number = self._device.heat_pump.serial_number
            wpm_device_id = f"{wpm_serial_number}_{description.component.value}"

            self._attr_unique_id = f"{wpm_device_id}_{description.key}"

            wpm_device = registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, wpm_serial_number)},
                manufacturer="Ovum",
                model=self._device.heat_pump.name or "Mira",
                translation_key="heat_pump",
                serial_number=wpm_serial_number,
                sw_version=self._device.heat_pump.version,
                via_device_id=hsm_device.id,
            )

            self._attr_device_info = DeviceInfo(
                identifiers=wpm_device.identifiers,
                manufacturer=wpm_device.manufacturer,
                model=wpm_device.model,
                name=wpm_device.name,
                serial_number=wpm_device.serial_number,
                sw_version=wpm_device.sw_version,
                via_device_id=hsm_device.id,
            )

        else:
            hsm_device_id = f"{hsm_serial_number}_{description.component.value}"
            self._attr_unique_id = f"{hsm_device_id}_{description.key}"

            if description.component == Component.SYSTEM:
                self._attr_device_info = DeviceInfo(
                    identifiers=hsm_device.identifiers,
                    manufacturer=hsm_device.manufacturer,
                    model=hsm_device.model,
                    name=hsm_device.name,
                    serial_number=hsm_device.serial_number,
                    sw_version=hsm_device.sw_version,
                )
            else:
                self._attr_device_info = ChildDeviceInfo(
                    identifiers={(DOMAIN, hsm_device_id)},
                    parent_device_id=hsm_device.id,
                    translation_key=description.component.value,
                )

    @property
    def _license(self) -> OvumLicense:
        return self.coordinator.license

    @property
    def _device(self) -> OvumMira:
        return self.coordinator.device

    @property
    def _subsystem(self) -> OvumComponent:
        """Returns the subsystem this entity reads from based on its component."""
        return getattr(self.coordinator.device, self.entity_description.component)

    @property
    def _current_value(
        self,
    ) -> StateType | date | datetime | Decimal | bool | IntEnum | StrEnum:
        return getattr(
            self._subsystem,
            self.entity_description.attribute or self.entity_description.key,
        )

    def _log(self, message: str, *args: Any) -> None:
        _LOGGER.info(
            "[%s] " + message,
            self.entity_description.component.name.lower(),
            *args,
        )

    @classmethod
    def from_list(
        cls,
        entry: OvumConfigEntry,
        descriptions: tuple[OvumEntityDescription, ...],
        **kwargs: Any,
    ) -> dict[str, Self]:
        coordinator = entry.runtime_data
        entities = {}

        for description in descriptions:
            if description.license <= coordinator.license:
                key = f"{description.component}_{description.key}"
                entities[key] = cls(
                    coordinator=coordinator,
                    description=description,
                    **kwargs,
                )

        return entities


class OvumEntityWriting(OvumEntity):
    async def _write_value(self, value: Any, target: str | None = None):
        """Optimistically write a value.
        Not using `await self.coordinator.async_request_refresh()` to read fewer values.
        """
        if target is None:
            target = self.entity_description.attribute or self.entity_description.key

        await self._subsystem.async_write_datapoint(target, value)
        # force update (dashboard refresh issues)
        await self._device.async_poll((self.entity_description.component,))
