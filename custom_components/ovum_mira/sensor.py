"""Sensor platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from ovum_mira_modbus import (
    OvumBufferLoadingStatus,
    OvumBufferMode,
    OvumBufferType,
    OvumCoolBufferAvailable,
    OvumCoolBufferLoadingStatus,
    OvumFreshWaterStatus,
    OvumHeatingCircuitType,
    OvumHeatpumpStatus,
    OvumHotWaterAvailable,
    OvumHotWaterRequestStatus,
    OvumLicense,
    OvumPvReleaseStatus,
    OvumVacationStatus,
)

from .coordinator import OvumConfigEntry
from .entity import (
    OvumEntity,
    OvumEntityDescription,
    enum_options,
    has_heating,
)
from .enum import Component

type TSensorDescription = OvumSensorDescription | OvumMeasurementSensorDescription


@dataclass(frozen=True, kw_only=True)
class OvumSensorDescription(OvumEntityDescription, SensorEntityDescription):
    """Describes a sensor reading an attribute from an Ovum component."""


@dataclass(frozen=True, kw_only=True)
class OvumMeasurementSensorDescription(OvumEntityDescription, SensorEntityDescription):
    """Describes a sensor reading a measurement from an Ovum component."""

    state_class = SensorStateClass.MEASUREMENT


class OvumSensor(OvumEntity, SensorEntity):
    entity_description: TSensorDescription

    @override
    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the current value, mapping enums to lowercase string."""
        value = self._current_value

        if isinstance(value, bool):
            return "on" if value else "off"

        if isinstance(value, IntEnum):
            return value.name.lower()

        return value


_SYSTEM_SENSORS: tuple[TSensorDescription, ...] = (
    OvumMeasurementSensorDescription(
        component=Component.SYSTEM,
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        name="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
)

_HEATPUMP_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.HEAT_PUMP,
        key="status",
        translation_key="heat_pump_status",
        name="status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumHeatpumpStatus),
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="power_consumption",
        translation_key="power_consumption",
        name="power_consumption",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="power_production",
        translation_key="power_production",
        name="power_production",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="demand",
        translation_key="demand",
        name="demand",
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="condenser_input",
        translation_key="condenser_input",
        name="condenser_input",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="condenser_output",
        translation_key="condenser_output",
        name="condenser_output",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HEAT_PUMP,
        key="ontime",
        translation_key="ontime",
        name="ontime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
    ),
)


def _heating_descriptions(component: Component) -> tuple[TSensorDescription, ...]:
    if component == Component.HEATING_1 or component == Component.HEATING_2:
        hk_license = OvumLicense.BASIC
    else:
        hk_license = OvumLicense.PLUS

    return (
        OvumSensorDescription(
            component=component,
            license=hk_license,
            key="type",
            translation_key="heating_circuit_type",
            name="type",
            device_class=SensorDeviceClass.ENUM,
            options=enum_options(OvumHeatingCircuitType),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=hk_license,
            key="temperature_target",
            translation_key="temperature_target",
            name="temperature_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=hk_license,
            key="temperature",
            translation_key="temperature",
            name="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=(
                OvumLicense.PLUS
                if component != Component.HEATING_1
                else OvumLicense.BASIC
            ),
            key="room_temperature",
            translation_key="room_temperature",
            name="room_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="vacation_status",
            translation_key="vacation_status",
            name="vacation_status",
            device_class=SensorDeviceClass.ENUM,
            options=enum_options(OvumVacationStatus),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    )


_HOT_WATER_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="request_status",
        translation_key="hot_water_request_status",
        name="request_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumHotWaterRequestStatus),
    ),
    OvumSensorDescription(
        component=Component.HOT_WATER,
        key="available",
        translation_key="available",
        name="available",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumHotWaterAvailable),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        key="temperature_target",
        translation_key="temperature_target",
        name="temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        key="reservoir_temperature_target",
        translation_key="reservoir_temperature_target",
        name="reservoir_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        key="reservoir_temperature_top",
        translation_key="reservoir_temperature_top",
        name="reservoir_temperature_top",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        key="reservoir_temperature_bottom",
        translation_key="reservoir_temperature_bottom",
        name="reservoir_temperature_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumSensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="vacation_status",
        translation_key="vacation_status",
        name="vacation_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumVacationStatus),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="fresh_water_temperature_target",
        translation_key="fresh_water_temperature_target",
        name="fresh_water_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumSensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="fresh_water_status",
        translation_key="fresh_water_status",
        name="fresh_water_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumFreshWaterStatus),
    ),
    OvumMeasurementSensorDescription(
        component=Component.HOT_WATER,
        license=OvumLicense.PLUS,
        key="circulation_pump_temperature",
        translation_key="circulation_pump_temperature",
        name="circulation_pump_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_check=lambda hot_water, _: (
            hot_water.circulation_pump_temperature is not None
            and hot_water.circulation_pump_temperature > 0
        ),
    ),
)

_BUFFER_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.BUFFER,
        key="type",
        translation_key="buffer_type",
        name="type",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumBufferType),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OvumSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="mode",
        translation_key="buffer_mode",
        name="mode",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumBufferMode),
    ),
    OvumSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="loading_status",
        translation_key="buffer_loading_status",
        name="loading_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumBufferLoadingStatus),
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        key="temperature_target",
        translation_key="temperature_target",
        name="temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        key="temperature_top",
        translation_key="temperature_top",
        name="temperature_top",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_check=lambda buffer, _: (
            buffer.temperature_top is not None
        ),
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        key="temperature_bottom",
        translation_key="temperature_bottom",
        name="temperature_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_available",
        translation_key="cooling_available",
        name="cooling_available",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumCoolBufferAvailable),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_temperature_bottom",
        translation_key="cooling_temperature_bottom",
        name="cooling_temperature_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_check=lambda buffer, _: (
            buffer.cooling_available == OvumCoolBufferAvailable.YES
        ),
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_temperature_target",
        translation_key="cooling_temperature_target",
        name="cooling_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_check=lambda buffer, _: (
            buffer.cooling_available == OvumCoolBufferAvailable.YES
        ),
    ),
    OvumSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_loading_status",
        translation_key="buffer_cooling_loading_status",
        name="cooling_loading_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumCoolBufferLoadingStatus),
        entity_registry_enabled_check=lambda buffer, _: (
            buffer.cooling_available == OvumCoolBufferAvailable.YES
        ),
    ),
)

_EMS_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.EMS,
        license=OvumLicense.PLUS,
        key="pv_release_status_hot_water",
        translation_key="pv_release_status_hot_water",
        name="pv_release_status_hot_water",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumPvReleaseStatus),
    ),
    OvumSensorDescription(
        component=Component.EMS,
        license=OvumLicense.PLUS,
        key="pv_release_status_heating",
        translation_key="pv_release_status_heating",
        name="pv_release_status_heating",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumPvReleaseStatus),
    ),
    OvumSensorDescription(
        component=Component.EMS,
        license=OvumLicense.PLUS,
        key="pv_release_status_stage2_hot_water",
        translation_key="pv_release_status_stage2_hot_water",
        name="pv_release_status_stage2_hot_water",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumPvReleaseStatus),
    ),
    OvumSensorDescription(
        component=Component.EMS,
        license=OvumLicense.PLUS,
        key="pv_release_status_stage2_heating",
        translation_key="pv_release_status_stage2_heating",
        name="pv_release_status_stage2_heating",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumPvReleaseStatus),
    ),
)

SENSORS: tuple[TSensorDescription, ...] = (
    *_SYSTEM_SENSORS,
    *_HEATPUMP_SENSORS,
    *_HOT_WATER_SENSORS,
    *_BUFFER_SENSORS,
    *_EMS_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumSensor.from_list(entry, SENSORS).values())

    for component in Component.heating:
        if has_heating(entry, component):
            async_add_entities(
                OvumSensor.from_list(entry, _heating_descriptions(component)).values()
            )
