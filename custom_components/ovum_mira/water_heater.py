"""Water heater platform for Ovum Mira."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.water_heater import (
    STATE_HEAT_PUMP,
    STATE_OFF,
    STATE_ON,
    WaterHeaterEntity,
    WaterHeaterEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ovum_mira_modbus import (
    OvumHotWaterStatus,
)
from propcache.api import cached_property

from .coordinator import OvumConfigEntry
from .entity import OvumEntityDescription, OvumEntityWriting
from .enum import Component


@dataclass(frozen=True, kw_only=True)
class OvumWaterHeaterDescription(OvumEntityDescription, WaterHeaterEntityDescription):
    """Describes a water heater for an attribute from an OvumWaterHeater component."""


class OvumWaterHeater(OvumEntityWriting, WaterHeaterEntity):
    """Water hater entity for Ovum Mira."""

    entity_description: OvumWaterHeaterDescription

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_min_temp = 0
    _attr_max_temp = 67

    _attr_current_operation = STATE_HEAT_PUMP
    _attr_operation_list = [STATE_OFF, STATE_ON]

    # TODO there's actually an away mode based on license level
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.ON_OFF
    )

    @override
    @cached_property
    def current_operation(self) -> str | None:
        if self._subsystem.status == OvumHotWaterStatus.ON:
            return STATE_ON

        return STATE_OFF

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_ON:
            await self.async_turn_on()

        await self.async_turn_off()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write_value("status", OvumHotWaterStatus.OFF)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write_value("status", OvumHotWaterStatus.ON)

    @override
    @cached_property
    def target_temperature(self) -> float | None:
        return self._subsystem.temperature_target

    @override
    @cached_property
    def current_temperature(self) -> float | None:
        return self._subsystem.reservoir_temperature_bottom

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        self._attr_target_temperature = temperature
        await self._write_value("temperature_target", temperature)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OvumConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        OvumWaterHeater.from_list(
            entry,
            (
                OvumWaterHeaterDescription(
                    component=Component.HOT_WATER,
                    key="hot_water",
                    translation_key="hot_water",
                    name="hot_water",
                ),
            ),
        )
    )
