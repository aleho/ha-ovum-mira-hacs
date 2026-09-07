"""Climate platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ovum_mira_modbus import (
    OvumHeatingCircuitMode,
    OvumHeatingCircuitOperationMode,
    OvumHeatpumpStatus,
    OvumLicense,
)
from propcache.api import cached_property

from .coordinator import OvumConfigEntry
from .entity import OvumEntityDescription, OvumEntityWriting
from .enum import Component


@dataclass(frozen=True, kw_only=True)
class OvumClimateDescription(OvumEntityDescription, ClimateEntityDescription):
    """Describes a climate entity for an attribute from an OvumClimate component."""


class OvumClimateHeating(OvumEntityWriting, ClimateEntity):
    """Climate entity for Ovum heating circuits."""

    entity_description: OvumClimateDescription

    _attr_hvac_mode = HVACMode.AUTO
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT, HVACMode.COOL]

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF
    )

    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = PRECISION_HALVES
    _attr_min_temp = 0
    _attr_max_temp = 50
    _attr_target_temperature_low = 0
    _attr_target_temperature_high = 50

    @override
    @cached_property
    def hvac_action(self) -> HVACAction:
        match self._device.heat_pump.status:
            case OvumHeatpumpStatus.HEATING:
                return HVACAction.HEATING
            case OvumHeatpumpStatus.COOLING:
                return HVACAction.COOLING
            case OvumHeatpumpStatus.DEFROSTING | OvumHeatpumpStatus.MANUAL_DEFROST:
                return HVACAction.DEFROSTING
            case OvumHeatpumpStatus.OIL_PREHEATING:
                return HVACAction.PREHEATING
            case (
                OvumHeatpumpStatus.HOLD_OFF
                | OvumHeatpumpStatus.STANDBY
                | OvumHeatpumpStatus.HOT_WATER
                | OvumHeatpumpStatus.LIMIT_UNDERCUT
                | OvumHeatpumpStatus.INVERTER_RESET
            ):
                return HVACAction.IDLE

        return HVACAction.OFF

    @override
    @cached_property
    def hvac_mode(self) -> HVACMode | None:
        """Tries to match the circuit mode to the HVAC mode."""
        match self._subsystem.mode:
            case OvumHeatingCircuitMode.AUTO:
                mode = HVACMode.AUTO
            case OvumHeatingCircuitMode.WINTER:
                mode = HVACMode.HEAT
            case OvumHeatingCircuitMode.SUMMER:
                mode = HVACMode.COOL
            case _:
                mode = HVACMode.OFF

        self._log("Matched mode %s to HVAC %s", self._subsystem.mode, mode)

        return mode

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Tries to match the circuit mode to the HVAC mode."""
        mode = None

        match hvac_mode:
            case HVACMode.OFF:
                mode = OvumHeatingCircuitMode.OFF
            case HVACMode.AUTO:
                mode = OvumHeatingCircuitMode.AUTO
            case HVACMode.HEAT:
                mode = OvumHeatingCircuitMode.WINTER
            case HVACMode.COOL:
                mode = OvumHeatingCircuitMode.SUMMER

        if mode is None:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

        self._log("Setting HVAC %s as mode %s", hvac_mode, mode)

        self._attr_hvac_mode = mode
        await self._write_value("mode", mode)

    async def async_turn_off(self) -> None:
        if self._device.mode != OvumHeatingCircuitMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            await self._write_value("mode", OvumHeatingCircuitMode.OFF)

    @override
    @cached_property
    def current_temperature(self) -> float | None:
        return self._subsystem.temperature

    @override
    @cached_property
    def target_temperature(self) -> float | None:
        """Return the target temperature.
        With cooling and heating a Plus license is required to set the cooling
        target.
        TODO is this implementation even correct?
        """
        if self._license == OvumLicense.BASIC:
            return self._subsystem.room_temperature_target

        if self._device.operation_mode == OvumHeatingCircuitOperationMode.HEATING:
            return self._subsystem.room_temperature_target

        if self._device.operation_mode == OvumHeatingCircuitOperationMode.COOLING:
            return self._subsystem.cooling_room_temperature_target

        if self._device.mode == OvumHeatingCircuitMode.SUMMER:
            return self._subsystem.cooling_room_temperature_target

        if self._device.mode == OvumHeatingCircuitMode.WINTER:
            return self._subsystem.room_temperature_target

        # in auto-mode we can only guess
        return self._subsystem.room_temperature_target

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        self._attr_target_temperature = temperature
        await self._write_value("room_temperature_target", temperature)


def _climate_description(component: Component) -> OvumClimateDescription:
    if component == Component.HEATING_1 or component == Component.HEATING_2:
        hk_license = OvumLicense.BASIC
    else:
        hk_license = OvumLicense.PLUS

    return OvumClimateDescription(
        component=component,
        license=hk_license,
        key=f"climate_{component.name.lower()}",
        translation_key=component.name.lower(),
        name=f"climate_{component.name.lower()}",
    )


ALL_HEATING: tuple[OvumClimateDescription, ...] = (
    _climate_description(Component.HEATING_1),
    _climate_description(Component.HEATING_2),
    _climate_description(Component.HEATING_3),
    _climate_description(Component.HEATING_4),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(OvumClimateHeating.from_list(entry, ALL_HEATING))
