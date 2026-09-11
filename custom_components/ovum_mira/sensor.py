"""Sensor platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum

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
    OvumEmsStatus,
    OvumFreshWaterStatus,
    OvumHeatingCircuitMode,
    OvumHeatingCircuitOperationMode,
    OvumHeatingCircuitType,
    OvumHeatpumpStatus,
    OvumHotWaterAvailable,
    OvumHotWaterRequestStatus,
    OvumHotWaterStatus,
    OvumLicense,
    OvumPvReleaseStatus,
    OvumVacationStatus,
)

from .coordinator import OvumConfigEntry
from .entity import OvumEntity, OvumEntityDescription, enum_options
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

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the current value, mapping enums to lowercase string."""
        value = getattr(
            self._subsystem,
            self.entity_description.attribute or self.entity_description.key,
        )

        if isinstance(value, IntEnum):
            return value.name.lower()

        return value


_SYSTEM_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.SYSTEM,
        key="serial_number",
        translation_key="serial_number",
        name="serial_number",
    ),
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
        key="serial_number",
        translation_key="serial_number",
        name="serial_number",
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
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


def _heating_description(component: Component) -> tuple[TSensorDescription, ...]:
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
        ),
        OvumSensorDescription(
            component=component,
            license=hk_license,
            key="mode",
            translation_key="heating_circuit_mode",
            name="mode",
            device_class=SensorDeviceClass.ENUM,
            options=enum_options(OvumHeatingCircuitMode),
        ),
        OvumSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="operation_mode",
            translation_key="heating_circuit_operation_mode",
            name="operation_mode",
            device_class=SensorDeviceClass.ENUM,
            options=enum_options(OvumHeatingCircuitOperationMode),
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
            license=hk_license,
            key="target_pv_plus",
            translation_key="target_pv_plus",
            name="target_pv_plus",
            device_class=SensorDeviceClass.TEMPERATURE_DELTA,
            native_unit_of_measurement=UnitOfTemperature.KELVIN,
            suggested_unit_of_measurement=UnitOfTemperature.KELVIN,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=hk_license,
            key="target_pv_minus",
            translation_key="target_pv_minus",
            name="target_pv_minus",
            device_class=SensorDeviceClass.TEMPERATURE_DELTA,
            native_unit_of_measurement=UnitOfTemperature.KELVIN,
            suggested_unit_of_measurement=UnitOfTemperature.KELVIN,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=hk_license,
            key="room_temperature_target",
            translation_key="room_temperature_target",
            name="room_temperature_target",
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
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="cooling_room_temperature_target",
            translation_key="cooling_room_temperature_target",
            name="cooling_room_temperature_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="heating_limit",
            translation_key="heating_limit",
            name="heating_limit",
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
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="vacation_status_heating_target",
            translation_key="vacation_status_heating_target",
            name="vacation_status_heating_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="vacation_status_cooling_target",
            translation_key="vacation_status_cooling_target",
            name="vacation_status_cooling_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="mode_fixed_heating_target",
            translation_key="mode_fixed_heating_target",
            name="mode_fixed_heating_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        OvumMeasurementSensorDescription(
            component=component,
            license=OvumLicense.PLUS,
            key="mode_fixed_cooling_target",
            translation_key="mode_fixed_cooling_target",
            name="mode_fixed_cooling_target",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
    )


_HOT_WATER_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.HOT_WATER,
        key="status",
        translation_key="off_on_state",
        name="status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumHotWaterStatus),
    ),
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
        key="temperature_target_pv",
        translation_key="temperature_target_pv",
        name="temperature_target_pv",
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
        key="temperature_target_pv",
        translation_key="temperature_target_pv",
        name="temperature_target_pv",
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
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_temperature_bottom",
        translation_key="cooling_temperature_bottom",
        name="cooling_temperature_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumMeasurementSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_temperature_target",
        translation_key="cooling_temperature_target",
        name="cooling_temperature_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    OvumSensorDescription(
        component=Component.BUFFER,
        license=OvumLicense.PLUS,
        key="cooling_loading_status",
        translation_key="buffer_cooling_loading_status",
        name="cooling_loading_status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumCoolBufferLoadingStatus),
    ),
)

_EMS_SENSORS: tuple[TSensorDescription, ...] = (
    OvumSensorDescription(
        component=Component.EMS,
        key="status",
        translation_key="ems_status",
        name="status",
        device_class=SensorDeviceClass.ENUM,
        options=enum_options(OvumEmsStatus),
    ),
    OvumMeasurementSensorDescription(
        component=Component.EMS,
        key="battery",
        translation_key="battery",
        name="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
    ),
    OvumMeasurementSensorDescription(
        component=Component.EMS,
        key="grid_power",
        translation_key="grid_power",
        name="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    OvumMeasurementSensorDescription(
        component=Component.EMS,
        key="inverter_power",
        translation_key="inverter_power",
        name="inverter_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    OvumMeasurementSensorDescription(
        component=Component.EMS,
        key="target_power",
        translation_key="target_power",
        name="target_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
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

ALL_SENSORS: tuple[TSensorDescription, ...] = (
    *_SYSTEM_SENSORS,
    *_HEATPUMP_SENSORS,
    *_heating_description(Component.HEATING_1),
    *_heating_description(Component.HEATING_2),
    *_heating_description(Component.HEATING_3),
    *_heating_description(Component.HEATING_4),
    *_HOT_WATER_SENSORS,
    *_BUFFER_SENSORS,
    *_EMS_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumSensor.from_list(entry, ALL_SENSORS))
