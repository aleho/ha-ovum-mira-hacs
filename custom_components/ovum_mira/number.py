"""Sensor platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ovum_mira_modbus import (
    OvumLicense,
)

from .coordinator import OvumConfigEntry
from .entity import (
    OvumEntityDescription,
    OvumEntityWriting,
    has_heating,
)
from .enum import Component


@dataclass(frozen=True, kw_only=True)
class OvumNumberDescription(OvumEntityDescription, NumberEntityDescription):
    """Describes a number entity for an Ovum component."""


class OvumNumber(OvumEntityWriting, NumberEntity):
    entity_description: OvumNumberDescription

    @override
    @property
    def native_value(self) -> float | None:
        value = self._current_value

        if isinstance(value, float):
            return value

        if isinstance(value, int):
            return float(value)

        return None

    @override
    async def async_set_native_value(self, value: float) -> None:
        await self._write_value(value)


_HOT_WATER_NUMBERS: tuple[OvumNumberDescription, ...] = (
    OvumNumberDescription(
        component=Component.HOT_WATER,
        key="temperature_target_pv",
        translation_key="temperature_target_pv",
        name="temperature_target_pv",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=67,
        native_step=1,
    ),
)


def _heating_descriptions(component: Component) -> tuple[OvumNumberDescription, ...]:
    if component == Component.HEATING_1 or component == Component.HEATING_2:
        hk_license = OvumLicense.BASIC
    else:
        hk_license = OvumLicense.PLUS

    return (
        OvumNumberDescription(
            component=component,
            license=hk_license,
            key="room_temperature_target",
            translation_key="room_temperature_target",
            name="room_temperature_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=0,
            native_max_value=50,
            native_step=0.5,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="cooling_room_temperature_target",
            translation_key="cooling_room_temperature_target",
            name="cooling_room_temperature_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=0,
            native_max_value=50,
            native_step=0.5,
        ),
        OvumNumberDescription(
            component=component,
            license=hk_license,
            key="target_pv_plus",
            translation_key="target_pv_plus",
            name="target_pv_plus",
            device_class=NumberDeviceClass.TEMPERATURE_DELTA,
            native_unit_of_measurement=UnitOfTemperature.KELVIN,
            native_min_value=0,
            native_max_value=25,
            native_step=1,
        ),
        OvumNumberDescription(
            component=component,
            license=hk_license,
            key="target_pv_minus",
            translation_key="target_pv_minus",
            name="target_pv_minus",
            device_class=NumberDeviceClass.TEMPERATURE_DELTA,
            native_unit_of_measurement=UnitOfTemperature.KELVIN,
            native_min_value=-25,
            native_max_value=0,
            native_step=1,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="heating_limit",
            translation_key="heating_limit",
            name="heating_limit",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-0,
            native_max_value=100,
            native_step=0.5,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="vacation_status_heating_target",
            translation_key="vacation_status_heating_target",
            name="vacation_status_heating_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-0,
            native_max_value=50,
            native_step=1,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="vacation_status_cooling_target",
            translation_key="vacation_status_cooling_target",
            name="vacation_status_cooling_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-0,
            native_max_value=50,
            native_step=1,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="mode_fixed_heating_target",
            translation_key="mode_fixed_heating_target",
            name="mode_fixed_heating_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-0,
            native_max_value=100,
            native_step=1,
        ),
        OvumNumberDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="mode_fixed_cooling_target",
            translation_key="mode_fixed_cooling_target",
            name="mode_fixed_cooling_target",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-0,
            native_max_value=100,
            native_step=1,
        ),
    )


_BUFFER_NUMBERS: tuple[OvumNumberDescription, ...] = (
    OvumNumberDescription(
        component=Component.BUFFER,
        key="temperature_target_pv",
        translation_key="temperature_target_pv",
        name="temperature_target_pv",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=70,
        native_step=1,
    ),
)

_EMS_NUMBERS: tuple[OvumNumberDescription, ...] = (
    OvumNumberDescription(
        component=Component.EMS,
        key="battery",
        translation_key="battery_soc",
        name="battery",
        device_class=NumberDeviceClass.BATTERY,
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        native_step=1,
        native_min_value=0,
        native_max_value=100,
    ),
    OvumNumberDescription(
        component=Component.EMS,
        key="grid_power",
        translation_key="grid_power",
        name="grid_power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_step=1,
    ),
    OvumNumberDescription(
        component=Component.EMS,
        key="inverter_power",
        translation_key="inverter_power",
        name="inverter_power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_step=1,
    ),
    OvumNumberDescription(
        component=Component.EMS,
        key="target_power",
        translation_key="target_power",
        name="target_power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_step=1,
    ),
)

NUMBER_ENTITIES: tuple[OvumNumberDescription, ...] = (
    *_HOT_WATER_NUMBERS,
    *_BUFFER_NUMBERS,
    *_EMS_NUMBERS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumNumber.from_list(entry, NUMBER_ENTITIES).values())

    for component in Component.heating:
        if has_heating(entry, component):
            async_add_entities(
                OvumNumber.from_list(entry, _heating_descriptions(component)).values()
            )
