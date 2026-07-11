"""Support for xsense buttons."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial

from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.device import Device
from .python_xsense.entity import Entity

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .python_xsense.async_xsense import AsyncXSense
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


async def run_action(entity: Entity, xsense: AsyncXSense, action: str) -> None:
    """Run an XSense action for either a child device or a station entity."""
    await xsense.action(entity, action)


async def wake_camera(entity: Entity, xsense: AsyncXSense) -> None:
    """Wake a sleeping camera through the Android app endpoint."""
    await xsense.wake_camera(entity)


def can_wake_camera(entity: Entity, xsense: AsyncXSense) -> bool:
    """Return if a camera supports the APK wake action."""
    return (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and entity.data.get("supportSleep") is True
    )


def camera_is_sleeping(entity: Entity) -> bool:
    """Return if the APK considers the camera to be sleeping."""
    return entity.data.get("deviceStatus") == 3


@dataclass(kw_only=True, frozen=True)
class XSenseButtonEntityDescription(ButtonEntityDescription):
    """Describes XSense button entity."""

    exists_fn: Callable[[Entity, AsyncXSense], bool] = lambda entity, api: True
    available_fn: Callable[[Entity], bool] = lambda entity: True
    press_fn: Callable[[Entity, AsyncXSense], Awaitable[None]]


BUTTONS: tuple[XSenseButtonEntityDescription, ...] = (
    XSenseButtonEntityDescription(
        key="test",
        translation_key="test",
        name="Test",
        icon="mdi:bell-ring",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "test"),
        press_fn=partial(run_action, action="test"),
    ),
    XSenseButtonEntityDescription(
        key="mute",
        translation_key="mute",
        name="Mute",
        icon="mdi:volume-off",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "mute"),
        press_fn=partial(run_action, action="mute"),
    ),
    XSenseButtonEntityDescription(
        key="fire_drill",
        translation_key="fire_drill",
        name="Fire Drill",
        icon="mdi:fire-alert",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "firedrill"),
        press_fn=partial(run_action, action="firedrill"),
    ),
    XSenseButtonEntityDescription(
        key="camera_wake",
        name="Wake Camera",
        icon="mdi:power-sleep",
        entity_category=EntityCategory.CONFIG,
        exists_fn=can_wake_camera,
        available_fn=camera_is_sleeping,
        press_fn=wake_camera,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the xsense button entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator_stations(coordinator).values():
        devices.extend(
            XSenseButtonEntity(coordinator, station, description)
            for description in BUTTONS
            if description.exists_fn(station, coordinator.xsense)
        )

    for dev in coordinator_devices(coordinator).values():
        devices.extend(
            XSenseButtonEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in BUTTONS
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

    @property
    def available(self) -> bool:
        """Return if this control can be used."""
        device = self._current_entity()
        return (
            device is not None
            and self._current_entity_is_online()
            and self.entity_description.available_fn(device)
        )

    async def async_press(self) -> None:
        """Press the button."""

        xsense = self.coordinator.xsense
        device = self._current_entity()
        if device is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        LOGGER.debug(
            "X-Sense button action requested: %s",
            _button_debug_context(device, self.entity_description.key),
        )
        try:
            await self.entity_description.press_fn(device, xsense)
        except Exception as err:
            LOGGER.debug(
                "X-Sense button action failed: %s",
                _button_debug_context(
                    device, self.entity_description.key, error=type(err).__name__
                ),
            )
            raise
        LOGGER.debug(
            "X-Sense button action completed: %s",
            _button_debug_context(device, self.entity_description.key),
        )


def _short_id(value):
    """Return a short diagnostic id without logging full serial-like values."""
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


def _button_debug_context(entity: Entity, action: str, **extra):
    """Return safe button action context without full serials."""
    station = getattr(entity, "station", None)
    context = {
        "action": action,
        "device": _short_id(getattr(entity, "sn", None)),
        "device_type": getattr(entity, "type", None),
        "station": _short_id(getattr(station, "sn", None)),
        "station_type": getattr(station, "type", None),
        "online": getattr(entity, "online", None),
    }
    context.update(extra)
    return context
