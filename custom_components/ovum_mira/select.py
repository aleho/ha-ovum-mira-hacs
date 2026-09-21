"""Sensor platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import override

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ovum_mira_modbus import (
    OvumEmsStatus,
    OvumHeatingCircuitMode,
    OvumHeatingCircuitOperationMode,
    OvumHotWaterStatus,
    OvumLicense,
)

from .coordinator import OvumConfigEntry
from .entity import (
    OvumEntityDescription,
    OvumEntityWriting,
    enum_options,
    has_heating,
)
from .enum import Component


@dataclass(frozen=True, kw_only=True)
class OvumSelectDescription(OvumEntityDescription, SelectEntityDescription):
    """Describes a select entity for an Ovum component."""

    ovum_enum: IntEnum | StrEnum

    @property
    def options(self) -> list[str]:
        return enum_options(self.ovum_enum)

    @options.setter
    def options(self, value) -> None:
        """Options aren't ever set"""
        pass


class OvumSelect(OvumEntityWriting, SelectEntity):
    entity_description: OvumSelectDescription

    @override
    @property
    def current_option(self) -> str | None:
        value = self._current_value

        if isinstance(value, IntEnum) or isinstance(value, StrEnum):
            self._debug("Current value %s=%s", value.name, value.value)
            return value.name.lower()

        if value is None:
            return None

        raise ValueError(f"Unsupported select value for enum: {value}")

    @override
    async def async_select_option(self, option: str) -> None:
        try:
            enum = self.entity_description.ovum_enum[option.upper()]
            self._debug("Writing value %s=%s", enum.name, enum.value)
            await self._write_value(enum)
        except Exception as err:
            raise ValueError(f"Unsupported select option for enum: {option}") from err


def _heating_descriptions(component: Component) -> tuple[OvumSelectDescription, ...]:
    if component == Component.HEATING_1 or component == Component.HEATING_2:
        hk_license = OvumLicense.BASIC
    else:
        hk_license = OvumLicense.PLUS

    return (
        OvumSelectDescription(
            component=component,
            license=hk_license,
            key="mode",
            translation_key="heating_circuit_mode",
            name="mode",
            ovum_enum=OvumHeatingCircuitMode,
        ),
        OvumSelectDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="operation_mode",
            translation_key="heating_circuit_operation_mode",
            name="operation_mode",
            ovum_enum=OvumHeatingCircuitOperationMode,
        ),
    )


_HOT_WATER_SELECTS: tuple[OvumSelectDescription, ...] = (
    OvumSelectDescription(
        component=Component.HOT_WATER,
        key="status",
        translation_key="hot_water_status",
        name="status",
        ovum_enum=OvumHotWaterStatus,
    ),
)

_EMS_SELECTS: tuple[OvumSelectDescription, ...] = (
    OvumSelectDescription(
        component=Component.EMS,
        key="status",
        translation_key="ems_status",
        name="status",
        ovum_enum=OvumEmsStatus,
    ),
)

SELECT_ENTITIES: tuple[OvumSelectDescription, ...] = (
    *_HOT_WATER_SELECTS,
    *_EMS_SELECTS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumSelect.from_list(entry, SELECT_ENTITIES).values())

    for component in Component.heating:
        if has_heating(entry, component):
            async_add_entities(
                OvumSelect.from_list(entry, _heating_descriptions(component)).values()
            )
