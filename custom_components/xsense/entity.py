"""Generic XSense Entity Class."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from xsense.entity import Entity

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import ATTR_VIA_DEVICE, CONF_EMAIL
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
)
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import XSenseDataUpdateCoordinator


@dataclass(kw_only=True, frozen=True)
class XSenseSensorEntityDescription(SensorEntityDescription):
    """Describes XSense sensor entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True
    value_fn: Callable[[Entity], StateType]


@dataclass(kw_only=True, frozen=True)
class XSenseBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes XSense binary-sensor entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True
    value_fn: Callable[[Entity], bool]


class XSenseEntity(CoordinatorEntity[XSenseDataUpdateCoordinator]):
    """Represent a XSense Entity."""

    _attr_has_entity_name = True
    _station_id: str | None = None

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        station_id: str | None = None,
    ) -> None:
        """Initialise the gateway."""
        super().__init__(coordinator)
        self._dev_id = entity.entity_id

        self._attr_unique_id = (
            f"{entity.entity_id}-{self.entity_description.key}".replace(
                "_", "-"
            ).lower()
        )

        connections = set()
        if "mac" in entity.data:
            connections.add((CONNECTION_NETWORK_MAC, entity.data["mac"]))
        if "macBT" in entity.data:
            connections.add((CONNECTION_BLUETOOTH, entity.data["macBT"]))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entity.entity_id)},
            connections=connections,
            manufacturer=MANUFACTURER,
            serial_number=entity.data.get("stationSN"),
            model=entity.type,
            name=entity.name,
        )
        if station_id:
            parent = (DOMAIN, station_id)
        else:
            parent = (DOMAIN, coordinator.entry.data[CONF_EMAIL])

        self._attr_device_info.update({ATTR_VIA_DEVICE: parent})

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._station_id:
            entity = self.coordinator.data["devices"][self._dev_id]
        else:
            entity = self.coordinator.data["stations"][self._dev_id]

        return entity.online not in ("0", False) and super().available
