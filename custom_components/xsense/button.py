"""Support for xsense buttons."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial

from .api.async_xsense import CAMERA_TYPES
from .api.device import Device
from .api.entity import Entity
from .api.entity_map import entities
from .api.exceptions import XSenseError

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .api.async_xsense import AsyncXSense
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


async def run_action(entity: Entity, xsense: AsyncXSense, action: str) -> None:
    """Run an XSense action for either a child device or a station entity."""
    entity_def = entities.get(entity.type)
    if not entity_def:
        raise XSenseError(
            f"Entity type {entity.type} is unknown, action {action} not possible"
        )

    action_def = next(
        (
            item
            for item in entity_def.get("actions", [])
            if item.get("action") == action
        ),
        None,
    )
    if not action_def:
        raise XSenseError(
            f"Action {action} is not supported for entity type {entity.type}"
        )

    topic = action_def.get("topic")
    if callable(topic):
        topic = topic(entity)
    if not topic:
        raise XSenseError(f"Action {action} for entity type {entity.type} has no topic")

    shadow = action_def["shadow"]
    if callable(shadow):
        shadow = shadow(entity)

    station = getattr(entity, "station", entity)
    desired = {
        "deviceSN": entity.sn,
        "shadow": shadow,
        "stationSN": station.sn,
        "time": datetime.now().strftime("%Y%m%d%H%M%S"),
        "userId": xsense.userid,
    }
    desired.update(action_def.get("extra", {}))
    action_data = action_def.get("data", {})
    if callable(action_data):
        action_data = action_data(entity)
    desired.update(action_data)

    await xsense.do_thing(station, topic, {"state": {"desired": desired}})


async def wake_camera(entity: Entity, xsense: AsyncXSense) -> None:
    """Wake a sleeping camera through the Android app endpoint."""
    await xsense.wake_camera(entity)


@dataclass(kw_only=True, frozen=True)
class XSenseButtonEntityDescription(ButtonEntityDescription):
    """Describes XSense button entity."""

    exists_fn: Callable[[Entity, AsyncXSense], bool] = lambda entity, api: True
    press_fn: Callable[[Entity, AsyncXSense], Awaitable[None]]


BUTTONS: tuple[XSenseButtonEntityDescription, ...] = (
    XSenseButtonEntityDescription(
        key="test",
        translation_key="test",
        name="Test",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "test"),
        press_fn=partial(run_action, action="test"),
    ),
    XSenseButtonEntityDescription(
        key="mute",
        translation_key="mute",
        name="Mute",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "mute"),
        press_fn=partial(run_action, action="mute"),
    ),
    XSenseButtonEntityDescription(
        key="fire_drill",
        translation_key="fire_drill",
        name="Fire Drill",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: xsense.has_action(entity, "firedrill"),
        press_fn=partial(run_action, action="firedrill"),
    ),
    XSenseButtonEntityDescription(
        key="camera_wake",
        name="Wake Camera",
        icon="mdi:power-sleep",
        entity_category=EntityCategory.CONFIG,
        exists_fn=lambda entity, xsense: (
            entity.type in CAMERA_TYPES and entity.data.get("supportSleep", False)
        ),
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

    for station in coordinator.data["stations"].values():
        devices.extend(
            XSenseButtonEntity(coordinator, station, description)
            for description in BUTTONS
            if description.exists_fn(station, coordinator.xsense)
        )

    for dev in coordinator.data["devices"].values():
        devices.extend(
            XSenseButtonEntity(
                coordinator, dev, description, station_id=dev.station.entity_id
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

    async def async_press(self) -> None:
        """Press the button."""

        xsense = self.coordinator.xsense
        device = self._current_entity()
        if device is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        await self.entity_description.press_fn(device, xsense)
