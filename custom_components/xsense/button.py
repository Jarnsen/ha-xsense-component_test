"""Support for xsense buttons."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial

from xsense.device import Device
from xsense.entity import Entity

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AsyncXSense, XSenseDataUpdateCoordinator
from .entity import XSenseEntity


async def run_action(entity: Entity, xsense: AsyncXSense, action: str):
    """Wrap xsense method in a async callable."""
    return await xsense.action(entity, action)


@dataclass(kw_only=True, frozen=True)
class XSenseButtonEntityDescription(ButtonEntityDescription):
    """Describes XSense button entity."""

    exists_fn: Callable[[Entity, AsyncXSense], bool] = lambda entity, api: True
    press_fn: Callable[[Entity, AsyncXSense], Awaitable[bool]]


SENSORS: tuple[XSenseButtonEntityDescription, ...] = (
    XSenseButtonEntityDescription(
        key="test",
        translation_key="test",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "test"),
        press_fn=partial(run_action, action="test"),
    ),
    # XSenseButtonEntityDescription(
    #     key="mute",
    #     translation_key="mute",
    #     entity_category=EntityCategory.CONFIG,
    #     exists_fn=lambda entity, xsense: xsense.has_action(entity, "mute"),
    #     press_fn=partial(run_action, action="mute"),
    # ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the xsense binary sensor entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator.data["stations"].values():
        devices.extend(
            XSenseButtonEntity(coordinator, station, description)
            for description in SENSORS
            if description.exists_fn(station, coordinator.xsense)
        )

    for dev in coordinator.data["devices"].values():
        devices.extend(
            XSenseButtonEntity(
                coordinator, dev, description, station_id=dev.station.entity_id
            )
            for description in SENSORS
            if description.exists_fn(dev, coordinator.xsense)
        )

    async_add_entities(devices)


class XSenseButtonEntity(XSenseEntity, ButtonEntity):
    """Buttons for xsense."""

    entity_description: XSenseButtonEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseButtonEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self.entity_description = entity_description
        self._attr_available = False  # This overrides the default

        super().__init__(coordinator, entity, station_id)

    async def async_press(self) -> None:
        """Press the button."""

        xsense = self.coordinator.xsense

        if self._station_id:
            device = self.coordinator.data["devices"][self._dev_id]
        else:
            device = self.coordinator.data["stations"][self._dev_id]

        await self.entity_description.press_fn(device, xsense)
