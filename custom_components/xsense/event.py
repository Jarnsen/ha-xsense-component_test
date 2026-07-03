"""Support for X-Sense event entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from .api.async_xsense import is_camera_entity
from .api.device import Device
from .api.entity import Entity

from homeassistant import config_entries
from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from .const import CAMERA_AI_SERVICE_AVAILABLE, DOMAIN, LOGGER
from .entity import XSenseEntity, coordinator_devices
from .frontend import FRONTEND_URL_PATH as RECORDINGS_PANEL_PATH
from .playback import PLAYBACK_PANEL_PATH, playback_url

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


AI_DETECTION_EVENT_TYPE = "ai_detection"
MOTION_EVENT_TYPE = "motion"
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

_CAMERA_ENTITY_DESCRIPTION_KEY = "thumbnail"

@dataclass(kw_only=True, frozen=True)
class XSenseEventEntityDescription(EventEntityDescription):
    """Describes X-Sense event entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True


AI_DETECTION_DESCRIPTION = XSenseEventEntityDescription(
    key=AI_DETECTION_EVENT_TYPE,
    translation_key="ai_detection",
    device_class=EventDeviceClass.MOTION,
    event_types=[AI_DETECTION_EVENT_TYPE, *AI_DETECTION_TYPES],
    exists_fn=is_camera_entity,
)

MOTION_DESCRIPTION = XSenseEventEntityDescription(
    key=MOTION_EVENT_TYPE,
    translation_key="motion",
    device_class=EventDeviceClass.MOTION,
    event_types=[MOTION_EVENT_TYPE],
    exists_fn=is_camera_entity,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense event entities."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            *_ai_detection_event_entities(coordinator),
            *_motion_event_entities(coordinator),
        ]
    )


class XSenseEventEntity(XSenseEntity, EventEntity):
    """Representation of an X-Sense event entity."""

    entity_description: XSenseEventEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseEventEntityDescription,
        station_id: str | None = None,
        device_entity: bool = False,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self._device_entity = device_entity
        self.entity_description = entity_description
        if (
            entity_description.key == AI_DETECTION_EVENT_TYPE
            and entity.data.get(CAMERA_AI_SERVICE_AVAILABLE) is False
        ):
            self._attr_entity_registry_enabled_default = False
        self._last_ai_detection_fingerprint: tuple[Any, ...] | None = None
        self._ai_detection_initialized = False
        super().__init__(coordinator, entity, station_id)

    def _current_entity(self) -> Entity | None:
        """Return the current coordinator entity for this event entity."""
        if self._device_entity:
            return coordinator_devices(self.coordinator).get(self._dev_id)
        return super()._current_entity()

    def _add_camera_event_context(
        self, entity: Entity, event_data: dict[str, Any] | None
    ) -> None:
        """Add camera context fields for automation templates."""
        if event_data is None:
            return
        if camera_name := getattr(entity, "name", None):
            event_data["camera_name"] = str(camera_name)
        if camera_entity_id := _camera_entity_id_for_event(self.hass, entity):
            event_data["camera_entity_id"] = camera_entity_id

    def _add_recording_playback_url(
        self, entity: Entity, event_data: dict[str, Any] | None
    ) -> None:
        """Add a Home Assistant playback URL for X-Sense SD recording events."""
        if event_data is None or event_data.get("recording_url"):
            return
        playback = event_data.get("playback")
        if not isinstance(playback, dict) or playback.get("source") != "sd_playback":
            return
        start_time = _recording_epoch_seconds(
            _first_present(
                playback,
                "start_time_s",
                "start_time",
                "timestamp_s",
                "timestamp",
            )
        )
        if start_time in (None, "") or not getattr(entity, "sn", None):
            return
        camera_entity_id = event_data.get(
            "camera_entity_id"
        ) or _camera_entity_id_for_event(
            self.hass,
            entity,
        )
        if camera_entity_id is None:
            return
        end_time = _recording_epoch_seconds(
            _first_present(playback, "end_time_s", "end_time")
        )
        if end_time in (None, ""):
            end_time = _recording_end_from_period(start_time, playback.get("period"))
        event_data["recording_url"] = playback_url(
            self.coordinator.entry.entry_id,
            str(entity.sn),
            int(start_time),
            camera_entity_id,
            end_time=end_time,
        )
        event_data["recording_source"] = "sd_playback"

    def _trigger_event_after_recording_cache(
        self,
        event_type: str,
        entity: Entity,
        event_data: dict[str, Any] | None,
    ) -> bool:
        """Cache recording metadata before firing a notification-capable event."""
        return _trigger_event_after_recording_cache(self, event_type, entity, event_data)

    def _handle_coordinator_update(self) -> None:
        """Handle updated coordinator data."""
        entity = self._current_entity()
        if entity is None:
            return

        event_data = ai_detection_event_data(entity.data)
        self._add_camera_event_context(entity, event_data)
        self._add_recording_playback_url(entity, event_data)
        fingerprint = ai_detection_fingerprint(event_data)
        if fingerprint is None:
            if not self._ai_detection_initialized:
                self._ai_detection_initialized = True
            self._write_state_if_added()
            return

        if not self._ai_detection_initialized:
            self._last_ai_detection_fingerprint = fingerprint
            self._ai_detection_initialized = True
            self._write_state_if_added()
            return

        if fingerprint == self._last_ai_detection_fingerprint:
            self._write_state_if_added()
            return

        self._last_ai_detection_fingerprint = fingerprint
        objects = event_data["objects"]
        event_type = objects[0] if len(objects) == 1 else AI_DETECTION_EVENT_TYPE
        if not self._trigger_event_after_recording_cache(event_type, entity, event_data):
            self._trigger_event(event_type, event_data)
        self._write_state_if_added()

    def _write_state_if_added(self) -> None:
        """Write HA state after the entity is registered."""
        if (
            getattr(self, "hass", None) is None
            or getattr(self, "platform", None) is None
        ):
            return
        self.async_write_ha_state()


class XSenseMotionEventEntity(XSenseEntity, EventEntity):
    """Representation of an X-Sense camera motion history event entity."""

    entity_description: XSenseEventEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseEventEntityDescription,
        station_id: str | None = None,
        device_entity: bool = False,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self._device_entity = device_entity
        self.entity_description = entity_description
        self._last_motion_fingerprint: tuple[Any, ...] | None = None
        self._motion_initialized = False
        super().__init__(coordinator, entity, station_id)

    def _current_entity(self) -> Entity | None:
        """Return the current coordinator entity for this event entity."""
        if self._device_entity:
            return coordinator_devices(self.coordinator).get(self._dev_id)
        return super()._current_entity()

    def _trigger_event_after_recording_cache(
        self,
        event_type: str,
        entity: Entity,
        event_data: dict[str, Any] | None,
    ) -> bool:
        """Cache recording metadata before firing a notification-capable event."""
        return _trigger_event_after_recording_cache(self, event_type, entity, event_data)

    def _handle_coordinator_update(self) -> None:
        """Handle updated coordinator data."""
        entity = self._current_entity()
        if entity is None:
            return

        event_data = motion_event_data(entity.data)
        self._add_camera_event_context(entity, event_data)
        self._add_motion_playback_url(entity, event_data)
        fingerprint = motion_fingerprint(event_data)
        if fingerprint is None:
            if not self._motion_initialized:
                self._motion_initialized = True
            self._write_state_if_added()
            return

        if not self._motion_initialized:
            self._last_motion_fingerprint = fingerprint
            self._motion_initialized = True
            self._write_state_if_added()
            return

        if fingerprint == self._last_motion_fingerprint:
            self._write_state_if_added()
            return

        self._last_motion_fingerprint = fingerprint
        if not self._trigger_event_after_recording_cache(
            MOTION_EVENT_TYPE,
            entity,
            event_data,
        ):
            self._trigger_event(MOTION_EVENT_TYPE, event_data)
        self._write_state_if_added()

    def _add_camera_event_context(
        self, entity: Entity, event_data: dict[str, Any] | None
    ) -> None:
        """Add camera context fields for automation templates."""
        if event_data is None:
            return
        if camera_name := getattr(entity, "name", None):
            event_data["camera_name"] = str(camera_name)
        if camera_entity_id := _camera_entity_id_for_event(self.hass, entity):
            event_data["camera_entity_id"] = camera_entity_id

    def _add_motion_playback_url(
        self, entity: Entity, event_data: dict[str, Any] | None
    ) -> None:
        """Add a Home Assistant playback URL for X-Sense SD recording events."""
        if event_data is None or event_data.get("recording_url"):
            return
        playback = event_data.get("playback")
        if not isinstance(playback, dict) or playback.get("source") != "sd_playback":
            return
        start_time = _recording_epoch_seconds(
            _first_present(
                playback,
                "start_time_s",
                "start_time",
                "timestamp_s",
                "timestamp",
            )
        )
        if start_time in (None, "") or not getattr(entity, "sn", None):
            return
        camera_entity_id = event_data.get(
            "camera_entity_id"
        ) or _camera_entity_id_for_event(
            self.hass,
            entity,
        )
        if camera_entity_id is None:
            return
        end_time = _recording_epoch_seconds(
            _first_present(playback, "end_time_s", "end_time")
        )
        if end_time in (None, ""):
            end_time = _recording_end_from_period(start_time, playback.get("period"))
        event_data["recording_url"] = playback_url(
            self.coordinator.entry.entry_id,
            str(entity.sn),
            int(start_time),
            camera_entity_id,
            end_time=end_time,
        )
        event_data["recording_source"] = "sd_playback"

    def _write_state_if_added(self) -> None:
        """Write HA state after the entity is registered."""
        if (
            getattr(self, "hass", None) is None
            or getattr(self, "platform", None) is None
        ):
            return
        self.async_write_ha_state()


def _ai_detection_event_entities(
    coordinator: XSenseDataUpdateCoordinator,
) -> list[XSenseEventEntity]:
    """Return X-Sense event entities for supported cameras."""
    entities: list[XSenseEventEntity] = []
    data = coordinator.data or {}
    stations = data.get("stations", {})
    devices = data.get("devices", {})

    for station in stations.values():
        if AI_DETECTION_DESCRIPTION.exists_fn(station):
            entities.append(
                XSenseEventEntity(coordinator, station, AI_DETECTION_DESCRIPTION)
            )

    for device in devices.values():
        if not AI_DETECTION_DESCRIPTION.exists_fn(device):
            continue

        entities.append(
            XSenseEventEntity(
                coordinator,
                device,
                AI_DETECTION_DESCRIPTION,
                station_id=_device_station_id(device),
                device_entity=True,
            )
        )

    return entities


def _motion_event_entities(
    coordinator: XSenseDataUpdateCoordinator,
) -> list[XSenseMotionEventEntity]:
    """Return X-Sense motion event entities for supported cameras."""
    entities: list[XSenseMotionEventEntity] = []
    data = coordinator.data or {}
    stations = data.get("stations", {})
    devices = data.get("devices", {})

    for station in stations.values():
        if MOTION_DESCRIPTION.exists_fn(station):
            entities.append(
                XSenseMotionEventEntity(coordinator, station, MOTION_DESCRIPTION)
            )

    for device in devices.values():
        if not MOTION_DESCRIPTION.exists_fn(device):
            continue

        entities.append(
            XSenseMotionEventEntity(
                coordinator,
                device,
                MOTION_DESCRIPTION,
                station_id=_device_station_id(device),
                device_entity=True,
            )
        )

    return entities


def _device_station_id(device: Device) -> str | None:
    """Return the parent station ID for a device entity."""
    station = getattr(device, "station", None)
    if station is None:
        return None
    return getattr(station, "entity_id", None)


def _camera_entity_id_for_event(hass: HomeAssistant, entity: Entity) -> str | None:
    """Return the HA camera entity id for an X-Sense camera record."""
    entity_id = getattr(entity, "entity_id", None)
    if not entity_id:
        return None
    unique_id = (
        f"{entity_id}-{_CAMERA_ENTITY_DESCRIPTION_KEY}".replace(
            "_", "-"
        ).lower()
    )
    registry = er.async_get(hass)
    return registry.async_get_entity_id(Platform.CAMERA, DOMAIN, unique_id)


def motion_event_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return event data for the latest APK camera motion history record."""
    motion_time = data.get("eventTime") or data.get("time")
    if motion_time in (None, ""):
        return None

    event_data: dict[str, Any] = {"time": motion_time}
    playback = data.get("playback")
    if isinstance(playback, dict) and playback:
        event_data["playback"] = playback
        event_data.update(_recording_event_data(playback))
    return event_data


def _recording_event_data(playback: dict[str, Any]) -> dict[str, Any]:
    """Return flat recording fields for automation templates."""
    event_data: dict[str, Any] = {}
    if recording_url := playback.get("video_url"):
        event_data["recording_url"] = recording_url
        if recording_source := playback.get("source"):
            event_data["recording_source"] = recording_source
    if snapshot_url := playback.get("image_url") or playback.get("package_image_url"):
        event_data["snapshot_url"] = snapshot_url
    return event_data


def motion_fingerprint(
    event_data: dict[str, Any] | None,
) -> tuple[Any, ...] | None:
    """Return a stable duplicate-detection fingerprint for motion events."""
    if event_data is None:
        return None
    playback = event_data.get("playback")
    trace = playback.get("trace_id") if isinstance(playback, dict) else None
    return (event_data.get("time"), trace)


def _trigger_event_after_recording_cache(
    event_entity: EventEntity,
    event_type: str,
    entity: Entity,
    event_data: dict[str, Any] | None,
) -> bool:
    """Cache recording metadata before firing a notification-capable event."""
    if event_data is None:
        return False
    playback = event_data.get("playback")
    if not isinstance(playback, dict):
        return False
    hass = getattr(event_entity, "hass", None)
    if not hasattr(hass, "async_create_task"):
        return False
    event_received_at = monotonic()

    async def _async_cache_then_trigger() -> None:
        from .media_source import async_cache_recording_playback

        cache_started_at = monotonic()
        LOGGER.debug(
            "X-Sense event recording cache started before trigger: %s",
            {
                "camera": _masked_serial(getattr(entity, "sn", "")),
                "event_type": event_type,
                "source": playback.get("source"),
                "queue_elapsed_ms": int((cache_started_at - event_received_at) * 1000),
                "start_time": playback.get("start_time_s")
                or playback.get("start_time")
                or playback.get("timestamp_s")
                or playback.get("timestamp"),
                "end_time": playback.get("end_time_s") or playback.get("end_time"),
            },
        )
        try:
            cached_url = await async_cache_recording_playback(
                hass,
                entry_id=event_entity.coordinator.entry.entry_id,
                entity=entity,
                playback=playback,
                camera_entity_id=str(event_data.get("camera_entity_id") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("X-Sense event recording cache failed: %s", exc)
            event_data["recording_cache_error"] = str(exc)
            cached_url = ""
        cache_finished_at = monotonic()
        cache_elapsed_ms = int((cache_finished_at - cache_started_at) * 1000)
        total_elapsed_ms = int((cache_finished_at - event_received_at) * 1000)
        if not cached_url:
            event_data["recording_cache_ready"] = False
            event_data["recording_cache_elapsed_ms"] = cache_elapsed_ms
            event_data["recording_total_elapsed_ms"] = total_elapsed_ms
            LOGGER.debug(
                "X-Sense event recording cache did not produce media; firing event without cached media: %s",
                {
                    "camera": _masked_serial(getattr(entity, "sn", "")),
                    "event_type": event_type,
                    "source": playback.get("source"),
                    "cache_elapsed_ms": cache_elapsed_ms,
                    "total_elapsed_ms": total_elapsed_ms,
                    "has_recording_url": bool(event_data.get("recording_url")),
                    "has_cache_error": bool(event_data.get("recording_cache_error")),
                },
            )
            event_entity._trigger_event(event_type, event_data)
            return
        event_data["recording_media_url"] = cached_url
        event_data["recording_cache_ready"] = True
        event_data["recording_cache_elapsed_ms"] = cache_elapsed_ms
        event_data["recording_total_elapsed_ms"] = total_elapsed_ms
        recording_url = str(event_data.get("recording_url") or "")
        if not _is_ha_recording_panel_url(recording_url):
            event_data["recording_url"] = cached_url
        event_data["recording_source"] = "cached_media"
        LOGGER.debug(
            "X-Sense event recording cache finished before trigger: %s",
            {
                "camera": _masked_serial(getattr(entity, "sn", "")),
                "cached": True,
                "event_type": event_type,
                "source": playback.get("source"),
                "cache_elapsed_ms": cache_elapsed_ms,
                "total_elapsed_ms": total_elapsed_ms,
            },
        )
        event_entity._trigger_event(event_type, event_data)

    hass.async_create_task(_async_cache_then_trigger())
    return True


def _masked_serial(value: Any) -> str:
    """Return a short masked serial for debug logs."""
    text = str(value or "")
    if len(text) <= 6:
        return "..."
    return f"...{text[-6:]}"


def _is_ha_recording_panel_url(value: str) -> bool:
    """Return whether a URL targets an X-Sense HA recording panel."""
    if not value:
        return False
    if value.startswith((f"/{PLAYBACK_PANEL_PATH}", f"/{RECORDINGS_PANEL_PATH}")):
        return True
    parsed = urlparse(value)
    return parsed.path in {f"/{PLAYBACK_PANEL_PATH}", f"/{RECORDINGS_PANEL_PATH}"}


def _recording_end_from_period(start_time: Any, period: Any) -> int:
    """Return an SD recording end timestamp from APK period metadata."""
    try:
        return int(start_time) + max(0, int(period))
    except (TypeError, ValueError):
        return int(start_time)


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value from data."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _recording_epoch_seconds(value: Any) -> int | None:
    """Return epoch seconds for APK playback values that may be ms or seconds."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp > 10_000_000_000:
        timestamp //= 1000
    return timestamp


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
    fallback_time = data.get("time") or data.get("eventTime")
    if fallback_time is not None:
        for object_name in objects:
            object_times.setdefault(object_name, fallback_time)

    event_data: dict[str, Any] = {
        "objects": list(objects),
        "last_ai_detection": ",".join(objects),
    }
    playback = data.get("playback")
    if isinstance(playback, dict) and playback:
        event_data["playback"] = playback
        event_data.update(_recording_event_data(playback))
    if object_times:
        event_data["object_times"] = object_times
        event_data["time"] = max(str(value) for value in object_times.values())
    return event_data


def ai_detection_fingerprint(
    event_data: dict[str, Any] | None,
) -> tuple[Any, ...] | None:
    """Return a stable duplicate-detection fingerprint for AI events."""
    if event_data is None:
        return None
    object_times = event_data.get("object_times") or {}
    return (
        tuple(event_data["objects"]),
        tuple(sorted(object_times.items())),
        event_data.get("time"),
    )
