"""Base entity for Ovum Mira and helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
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


def enum_options(enum) -> list[str]:
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
        serial_number = entry.unique_id or "__no_serial_number__"
        device_id = f"{serial_number}_{description.component.value}"

        self._attr_unique_id = f"{device_id}_{description.key}"

        registry = device_registry.async_get(coordinator.hass)
        device = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, serial_number)},
            manufacturer="Ovum",
            model="Mira",
            name="Ovum Mira",
            serial_number=serial_number,
        )

        if description.component == Component.SYSTEM:
            self._attr_device_info = DeviceInfo(
                identifiers=device.identifiers,
                manufacturer=device.manufacturer,
                model=device.model,
                name=device.name,
                serial_number=device.serial_number,
            )
        else:
            self._attr_device_info = ChildDeviceInfo(
                identifiers={(DOMAIN, device_id)},
                parent_device_id=device.id,
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
    def _current_value(self) -> StateType | date | datetime | Decimal | bool:
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
    async def _write_value(self, target: str, value: Any):
        """Optimistically write a value.
        Not using `await self.coordinator.async_request_refresh()` to read fewer values.
        Currently, also not using `await self._subsystem.async_update()`.
        """
        await self._subsystem.async_write_datapoint(target, value)
        self.async_write_ha_state()
