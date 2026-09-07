"""Binary sensor platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ovum_mira_modbus import (
    OvumLicense,
)

from .coordinator import OvumConfigEntry
from .entity import OvumEntity, OvumEntityDescription
from .enum import Component


@dataclass(frozen=True, kw_only=True)
class OvumBinarySensorDescription(OvumEntityDescription, BinarySensorEntityDescription):
    """Describes a binary sensor reading an attribute from an Ovum component."""


class OvumBinarySensor(OvumEntity, BinarySensorEntity):
    entity_description: OvumBinarySensorDescription


_HOT_WATER_SENSORS: tuple[OvumBinarySensorDescription, ...] = (
    OvumBinarySensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="circulation_pump_status",
        translation_key="circulation_pump_status",
        name="circulation_pump_status",
    ),
)


ALL_SENSORS: tuple[OvumBinarySensorDescription, ...] = (*_HOT_WATER_SENSORS,)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumBinarySensor.from_list(entry, ALL_SENSORS))
