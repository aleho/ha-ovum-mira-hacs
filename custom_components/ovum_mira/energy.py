"""Energy sensor as integration from a power sensor."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.integration.const import METHOD_LEFT
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device import async_entity_id_to_device

from .const import DOMAIN
from .entity import OvumEntity


class OvumEnergySensor(IntegrationSensor):
    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        source_entity: OvumEntity,
        hass: HomeAssistant,
    ) -> None:
        source_description = source_entity.entity_description

        registry = entity_registry.async_get(hass)
        entity_id = registry.async_get_entity_id(
            domain="sensor",
            platform=DOMAIN,
            unique_id=source_entity.unique_id,
        )

        device = async_entity_id_to_device(hass, entity_id)

        super().__init__(
            source_entity=entity_id,
            device=device,
            unique_id=f"{source_entity.unique_id}_integral",
            integration_method=METHOD_LEFT,
            round_digits=0,
            max_sub_interval=timedelta(minutes=5),
            unit_time=UnitOfTime.HOURS,
            unit_prefix="k",
            name=None,
        )

        self._attr_translation_key = source_description.translation_key + "_integral"

        # delete attribute to re-enable use of translation key
        del self._attr_name
