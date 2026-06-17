"""Support for X-Sense event entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .api.async_xsense import is_camera_entity
from .api.entity import Entity

from homeassistant import config_entries
from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import XSenseEntity

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


AI_DETECTION_EVENT_TYPE = "ai_detection"
AI_DETECTION_TYPES: tuple[str, ...] = (
    "person",
    "pet",
    "vehicle",
    "vehicle_enter",
    "vehicle_out",
    "vehicle_held_up",
    "package",
    "package_drop_off",
    "package_pick_up",
    "package_exist",
    "other",
)

_AI_DETECTION_TIME_KEYS: dict[str, str] = {
    "person": "lastPersonDetectionTime",
    "pet": "lastPetDetectionTime",
    "vehicle": "lastVehicleDetectionTime",
    "vehicle_enter": "lastVehicleEnterDetectionTime",
    "vehicle_out": "lastVehicleOutDetectionTime",
    "vehicle_held_up": "lastVehicleHeldUpDetectionTime",
    "package": "lastPackageDetectionTime",
    "package_drop_off": "lastPackageDropOffDetectionTime",
    "package_pick_up": "lastPackagePickUpDetectionTime",
    "package_exist": "lastPackageExistDetectionTime",
    "other": "lastOtherDetectionTime",
}

_AI_DETECTION_DATA_KEYS = frozenset({"lastAiDetection", *_AI_DETECTION_TIME_KEYS.values()})


@dataclass(kw_only=True, frozen=True)
class XSenseEventEntityDescription(EventEntityDescription):
    """Describes X-Sense event entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True


AI_DETECTION_DESCRIPTION = XSenseEventEntityDescription(
    key=AI_DETECTION_EVENT_TYPE,
    translation_key="ai_detection",
    device_class=EventDeviceClass.MOTION,
    event_types=[AI_DETECTION_EVENT_TYPE, *AI_DETECTION_TYPES],
    exists_fn=lambda entity: is_camera_entity(entity)
    and (
        entity.data.get("supportPersonDetect") is not False
        or any(key in entity.data for key in _AI_DETECTION_DATA_KEYS)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense event entities."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        XSenseEventEntity(coordinator, station, AI_DETECTION_DESCRIPTION)
        for station in coordinator.data["stations"].values()
        if AI_DETECTION_DESCRIPTION.exists_fn(station)
    )


class XSenseEventEntity(XSenseEntity, EventEntity):
    """Representation of an X-Sense event entity."""

    entity_description: XSenseEventEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseEventEntityDescription,
    ) -> None:
        """Set up the instance."""
        self.entity_description = entity_description
        self._last_ai_detection_fingerprint: tuple[Any, ...] | None = None
        self._ai_detection_initialized = False
        super().__init__(coordinator, entity)

    def _handle_coordinator_update(self) -> None:
        """Handle updated coordinator data."""
        entity = self._current_entity()
        if entity is None:
            return

        event_data = ai_detection_event_data(entity.data)
        fingerprint = ai_detection_fingerprint(event_data)
        if fingerprint is None:
            if not self._ai_detection_initialized:
                self._ai_detection_initialized = True
            return

        if not self._ai_detection_initialized:
            self._last_ai_detection_fingerprint = fingerprint
            self._ai_detection_initialized = True
            return

        if fingerprint == self._last_ai_detection_fingerprint:
            return

        self._last_ai_detection_fingerprint = fingerprint
        objects = event_data["objects"]
        event_type = objects[0] if len(objects) == 1 else AI_DETECTION_EVENT_TYPE
        self._trigger_event(event_type, event_data)
        self.async_write_ha_state()


def ai_detection_event_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return event data for the latest APK AI detection payload."""
    raw_objects = data.get("lastAiDetection")
    if not isinstance(raw_objects, str) or not raw_objects.strip():
        return None

    objects = tuple(
        object_name.strip()
        for object_name in raw_objects.split(",")
        if object_name.strip() in AI_DETECTION_TYPES
    )
    if not objects:
        return None

    object_times = {
        object_name: data[time_key]
        for object_name, time_key in _AI_DETECTION_TIME_KEYS.items()
        if object_name in objects and time_key in data
    }
    event_data: dict[str, Any] = {
        "objects": list(objects),
        "last_ai_detection": ",".join(objects),
    }
    if object_times:
        event_data["object_times"] = object_times
        event_data["time"] = max(str(value) for value in object_times.values())
    return event_data


def ai_detection_fingerprint(event_data: dict[str, Any] | None) -> tuple[Any, ...] | None:
    """Return a stable duplicate-detection fingerprint for AI events."""
    if event_data is None:
        return None
    object_times = event_data.get("object_times") or {}
    return (
        tuple(event_data["objects"]),
        tuple(sorted(object_times.items())),
        event_data.get("time"),
    )
