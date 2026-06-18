"""Support for X-Sense numeric settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant import config_entries
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.async_xsense import is_camera_entity
from .api.device import Device
from .api.entity import Entity
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


def has_shadow_volume(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera X-Sense shadow exposes a writable volume field."""

    def exists(entity: Entity) -> bool:
        if is_camera_entity(entity) or key not in entity.data:
            return False
        if key == "alarmVol" and entity.type == "SBS50":
            return False
        return True

    return exists


@dataclass(kw_only=True, frozen=True)
class XSenseNumberEntityDescription(NumberEntityDescription):
    """Describes X-Sense number entity."""

    data_key: str
    exists_fn: Callable[[Entity], bool]
    entity_category: EntityCategory | None = EntityCategory.CONFIG


NUMBERS: tuple[XSenseNumberEntityDescription, ...] = (
    XSenseNumberEntityDescription(
        key="alarm_volume",
        data_key="alarmVol",
        translation_key="alarm_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("alarmVol"),
    ),
    XSenseNumberEntityDescription(
        key="voice_volume",
        data_key="voiceVol",
        translation_key="voice_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("voiceVol"),
    ),
    XSenseNumberEntityDescription(
        key="chirp_volume",
        data_key="chirpVol",
        translation_key="chirp_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("chirpVol"),
    ),
    XSenseNumberEntityDescription(
        key="reminder_volume",
        data_key="remindVol",
        translation_key="reminder_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("remindVol"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense number entities."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator_stations(coordinator).values():
        devices.extend(
            XSenseNumberEntity(coordinator, station, description)
            for description in NUMBERS
            if description.exists_fn(station)
        )

    for dev in coordinator_devices(coordinator).values():
        devices.extend(
            XSenseNumberEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in NUMBERS
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseNumberEntity(XSenseEntity, NumberEntity):
    """Numeric settings for X-Sense devices."""

    entity_description: XSenseNumberEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseNumberEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self.entity_description = entity_description
        self._attr_available = False
        super().__init__(coordinator, entity, station_id)

    @property
    def available(self) -> bool:
        """Return if this control can be used."""
        return self._current_entity_is_online()

    @property
    def native_value(self) -> float | None:
        """Return the number value."""
        entity = self._current_entity()
        if entity is None:
            return None
        value = entity.data.get(self.entity_description.data_key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the X-Sense numeric setting."""
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        int_value = round(value)
        await self.coordinator.xsense.update_shadow_volume(
            entity, self.entity_description.data_key, int_value
        )
        entity.data[self.entity_description.data_key] = int_value
        self.coordinator.async_update_listeners()
