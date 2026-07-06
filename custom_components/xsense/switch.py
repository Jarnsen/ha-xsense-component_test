"""Support for X-Sense switches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import voluptuous as vol

from .api.device import Device
from .api.entity import Entity
from .api.entity_map import EntityType
from .api.async_xsense import (
    CAMERA_AI_ASSISTANT_TYPES,
    CAMERA_AI_NOTIFICATION_TYPES,
    _camera_config_write_value,
    is_camera_entity,
)

from homeassistant import config_entries
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


ATTR_ENABLED = "enabled"
ATTR_END_TIME = "end_time"
ATTR_GROUP_ID = "group_id"
ATTR_DEVICE_IDS = "device_ids"
ATTR_NAME = "name"
ATTR_SCHEDULE_ID = "schedule_id"
ATTR_START_TIME = "start_time"
ATTR_TIME_ZONE = "time_zone"
ATTR_TIMER = "timer"
ATTR_VALUE = "value"
ATTR_WEEK_DAYS = "week_days"

LIGHT_SCHEDULE_CREATE_SCHEMA = {
    vol.Required(ATTR_NAME): cv.string,
    vol.Required(ATTR_START_TIME): cv.string,
    vol.Required(ATTR_END_TIME): cv.string,
    vol.Required(ATTR_WEEK_DAYS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
    vol.Optional(ATTR_TIME_ZONE): cv.string,
}

LIGHT_SCHEDULE_UPDATE_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_ID): cv.string,
    vol.Required(ATTR_START_TIME): cv.string,
    vol.Required(ATTR_END_TIME): cv.string,
    vol.Required(ATTR_WEEK_DAYS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
    vol.Optional(ATTR_TIME_ZONE): cv.string,
}

LIGHT_SCHEDULE_RENAME_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_ID): cv.string,
    vol.Required(ATTR_NAME): cv.string,
}

LIGHT_SCHEDULE_DELETE_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_ID): cv.string,
}

LIGHT_GROUP_CREATE_SCHEMA = {
    vol.Required(ATTR_NAME): cv.string,
}

LIGHT_GROUP_RENAME_SCHEMA = {
    vol.Required(ATTR_GROUP_ID): cv.string,
    vol.Required(ATTR_NAME): cv.string,
}

LIGHT_GROUP_TIMER_SCHEMA = {
    vol.Required(ATTR_GROUP_ID): cv.string,
    vol.Required(ATTR_TIMER): vol.In(["pirTime", "appTime"]),
    vol.Required(ATTR_VALUE): cv.string,
}

LIGHT_GROUP_BIND_SCHEMA = {
    vol.Required(ATTR_NAME): cv.string,
    vol.Required(ATTR_DEVICE_IDS): vol.All(cv.ensure_list, [cv.string]),
}

LIGHT_GROUP_DELETE_SCHEMA = {
    vol.Required(ATTR_GROUP_ID): cv.string,
}

LIGHT_GROUP_REMOVE_DEVICES_SCHEMA = {
    vol.Required(ATTR_DEVICE_IDS): vol.All(cv.ensure_list, [cv.string]),
}


def boolean_state(value) -> bool | None:
    """Return the normalized state for explicit X-Sense boolean payload values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on"}:
            return True
        if normalized in {"0", "false", "off"}:
            return False
    return None


def on_off_value(value: bool) -> str:
    """Return the X-Sense on/off payload value."""
    return "1" if value else "0"


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for an X-Sense data key."""
    return lambda entity: key in entity.data


def has_shadow_data(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera setting can be written through an app shadow."""
    return lambda entity: key in entity.data and _has_shadow_write_route(entity)


def _has_shadow_write_route(entity: Entity) -> bool:
    """Return if an entity has the serial context needed for shadow writes."""
    if is_camera_entity(entity) or not getattr(entity, "sn", None):
        return False
    station = getattr(entity, "station", entity)
    return bool(getattr(station, "sn", None) and getattr(station, "shadow_name", None))


def has_camera_data(key: str) -> Callable[[Entity], bool]:
    """Return if the app exposes an admin-only camera setting."""
    return lambda entity: (
        is_camera_entity(entity)
        and key in entity.data
        and entity.data.get("isAdmin") is True
    )


def has_supported_data(key: str, support_key: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a supported camera setting."""
    return lambda entity: (
        is_camera_entity(entity)
        and key in entity.data
        and entity.data.get("isAdmin") is True
        and entity.data.get(support_key) is True
    )


def has_apk_default_supported_data(
    key: str, support_key: str
) -> Callable[[Entity], bool]:
    """Return if the APK shows a camera setting when support is missing or enabled."""
    return lambda entity: (
        is_camera_entity(entity)
        and key in entity.data
        and entity.data.get("isAdmin") is True
        and entity.data.get(support_key) is not False
    )


def has_camera_person_detection(entity: Entity) -> bool:
    """Return if the app exposes the camera person detection setting."""
    return (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and (
            entity.data.get("supportPersonDetect") is True
            or (
                "devicePersonDetect" in entity.data
                and entity.data.get("supportPersonDetect") is not False
            )
        )
    )


def has_camera_ai_notification(event_type: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a camera AI notification category."""
    data_key = f"aiNotification{_camel_suffix(event_type)}"
    return lambda entity: (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and data_key in entity.data
        and event_type in entity.data.get("aiNotificationSupportedTypes", ())
    )


def has_camera_ai_assistant(event_object: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a camera AI assistant object switch."""
    data_key = f"aiAssistant{_camel_suffix(event_object)}"
    return lambda entity: (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and data_key in entity.data
        and event_object in entity.data.get("aiAssistantSupportedTypes", ())
    )


def data_bool(key: str) -> Callable[[Entity], bool | None]:
    """Return a value function for an X-Sense boolean data key."""
    return lambda entity: boolean_state(entity.data[key])


def optional_data_bool(key: str) -> Callable[[Entity], bool | None]:
    """Return a value function for optional X-Sense boolean data."""
    return lambda entity: boolean_state(entity.data.get(key))


def entity_topic(entity: Entity) -> str:
    """Return the settings shadow topic used by the X-Sense app."""
    station = getattr(entity, "station", None)
    if station and station.type == "SBS50":
        return f"2nd_cfg_{entity.sn}"
    return f"info_{entity.sn}"


def _camel_suffix(value: str) -> str:
    """Return PascalCase for snake-style APK object names."""
    return "".join(part.capitalize() for part in value.split("_") if part)


def _ai_notification_name(event_type: str) -> str:
    """Return a readable switch name for an AI notification category."""
    labels = {
        "person": "Person",
        "pet": "Pet",
        "vehicle_enter": "Vehicle Enter",
        "vehicle_out": "Vehicle Out",
        "vehicle_held_up": "Vehicle Held Up",
        "package_exist": "Package Present",
        "package_drop_off": "Package Drop-Off",
        "package_pick_up": "Package Pick-Up",
        "other": "Other",
    }
    return f"AI Notification {labels[event_type]}"


def _ai_assistant_name(event_object: str) -> str:
    """Return a readable switch name for an AI assistant object."""
    labels = {
        "person": "Person",
        "pet": "Pet",
        "vehicle": "Vehicle",
        "package": "Package",
    }
    return f"AI Assistant {labels[event_object]}"


@dataclass(kw_only=True, frozen=True)
class XSenseSwitchEntityDescription(SwitchEntityDescription):
    """Describes X-Sense switch entity."""

    data_key: str
    exists_fn: Callable[[Entity], bool]
    value_fn: Callable[[Entity], bool | None]
    read_key: str | None = None
    addx_key: str | None = None
    light_on_event: str | None = None
    write_value_fn: Callable[[bool], str] = on_off_value
    entity_category: EntityCategory | None = EntityCategory.CONFIG


SWITCHES: tuple[XSenseSwitchEntityDescription, ...] = (
    XSenseSwitchEntityDescription(
        key="led_light",
        data_key="ledLight",
        name="LED Light",
        icon="mdi:led-on",
        exists_fn=has_shadow_data("ledLight"),
        value_fn=data_bool("ledLight"),
    ),
    XSenseSwitchEntityDescription(
        key="light_power",
        data_key="on",
        name="Light Power",
        icon="mdi:lightbulb",
        entity_category=None,
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) is not None
            and entity.entity_type.value == "light"
            and "on" in entity.data
        ),
        value_fn=data_bool("on"),
    ),
    XSenseSwitchEntityDescription(
        key="alarm_enabled",
        data_key="alarmEnable",
        read_key="alarmEnabled",
        name="Alarm Enabled",
        icon="mdi:bell-check",
        exists_fn=lambda entity: (
            _has_shadow_write_route(entity)
            and ("alarmEnable" in entity.data or "alarmEnabled" in entity.data)
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("alarmEnable", entity.data.get("alarmEnabled"))
        ),
    ),
    XSenseSwitchEntityDescription(
        key="continued_alarm",
        data_key="continueAlarm",
        read_key="continuedAlarm",
        name="Continued Alarm",
        icon="mdi:bell-plus",
        exists_fn=lambda entity: (
            _has_shadow_write_route(entity)
            and ("continueAlarm" in entity.data or "continuedAlarm" in entity.data)
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("continueAlarm", entity.data.get("continuedAlarm"))
        ),
    ),
    XSenseSwitchEntityDescription(
        key="chirp_tone_enabled",
        data_key="chirpToneEnable",
        name="Chirp Tone Enabled",
        icon="mdi:volume-high",
        exists_fn=has_shadow_data("chirpToneEnable"),
        value_fn=data_bool("chirpToneEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="reminder_enabled",
        data_key="remindOn",
        name="Reminder Enabled",
        icon="mdi:bell-clock",
        exists_fn=has_shadow_data("remindOn"),
        value_fn=data_bool("remindOn"),
    ),
    XSenseSwitchEntityDescription(
        key="reminder_tone_enabled",
        data_key="remindToneEnable",
        name="Reminder Tone Enabled",
        icon="mdi:volume-high",
        exists_fn=has_shadow_data("remindToneEnable"),
        value_fn=data_bool("remindToneEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="await_enabled",
        data_key="awaitEnable",
        name="Await Enabled",
        icon="mdi:timer-sand",
        exists_fn=has_shadow_data("awaitEnable"),
        value_fn=data_bool("awaitEnable"),
        light_on_event="0",
    ),
    XSenseSwitchEntityDescription(
        key="pir_enabled",
        data_key="pirEnable",
        name="PIR Enabled",
        icon="mdi:motion-sensor",
        exists_fn=has_shadow_data("pirEnable"),
        value_fn=data_bool("pirEnable"),
        light_on_event="0",
    ),
    XSenseSwitchEntityDescription(
        key="sunshine_enabled",
        data_key="sunshineEnable",
        name="Sunshine Enabled",
        icon="mdi:white-balance-sunny",
        exists_fn=has_shadow_data("sunshineEnable"),
        value_fn=data_bool("sunshineEnable"),
        light_on_event="0",
    ),
    XSenseSwitchEntityDescription(
        key="key_sound_enabled",
        data_key="keySound",
        name="Key Sound Enabled",
        icon="mdi:volume-high",
        exists_fn=has_shadow_data("keySound"),
        value_fn=data_bool("keySound"),
    ),
    XSenseSwitchEntityDescription(
        key="warning_enabled",
        data_key="warnIsOpen",
        name="Warning Enabled",
        icon="mdi:alert",
        exists_fn=has_shadow_data("warnIsOpen"),
        value_fn=data_bool("warnIsOpen"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_motion_detection",
        data_key="needMotion",
        addx_key="needMotion",
        name="Motion Detection",
        icon="mdi:motion-sensor",
        exists_fn=has_camera_data("needMotion"),
        value_fn=data_bool("needMotion"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_person_detection",
        data_key="devicePersonDetect",
        addx_key="devicePersonDetect",
        name="Person Detection",
        icon="mdi:account-alert",
        exists_fn=has_camera_person_detection,
        value_fn=lambda entity: boolean_state(entity.data.get("devicePersonDetect")),
    ),
    XSenseSwitchEntityDescription(
        key="camera_video_recording",
        data_key="needVideo",
        addx_key="needVideo",
        name="Video Recording",
        icon="mdi:video-check",
        exists_fn=has_camera_data("needVideo"),
        value_fn=data_bool("needVideo"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_night_vision",
        data_key="needNightVision",
        addx_key="needNightVision",
        name="Night Vision",
        icon="mdi:weather-night",
        exists_fn=has_camera_data("needNightVision"),
        value_fn=data_bool("needNightVision"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_recording_light",
        data_key="recLamp",
        addx_key="recLamp",
        name="Recording Light",
        icon="mdi:led-on",
        exists_fn=has_supported_data("recLamp", "supportRecLamp"),
        value_fn=data_bool("recLamp"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_alarm",
        data_key="needAlarm",
        addx_key="needAlarm",
        name="Camera Alarm",
        icon="mdi:bell-check",
        exists_fn=has_supported_data("needAlarm", "supportAlarm"),
        value_fn=data_bool("needAlarm"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_mirror_flip",
        data_key="mirrorFlip",
        addx_key="mirrorFlip",
        name="Mirror Flip",
        icon="mdi:flip-horizontal",
        exists_fn=has_supported_data("mirrorFlip", "supportMirrorFlip"),
        value_fn=data_bool("mirrorFlip"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_antiflicker",
        data_key="antiflickerSwitch",
        addx_key="antiflickerSwitch",
        name="Anti-Flicker",
        icon="mdi:lightbulb-on-10",
        exists_fn=has_supported_data("antiflickerSwitch", "supportAntiFlicker"),
        value_fn=data_bool("antiflickerSwitch"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_cry_detection",
        data_key="cryDetect",
        addx_key="cryDetect",
        name="Cry Detection",
        icon="mdi:baby-face-outline",
        exists_fn=has_supported_data("cryDetect", "supportCryDetect"),
        value_fn=data_bool("cryDetect"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_cooldown",
        data_key="cooldownEnabled",
        addx_key="cooldown.userEnable",
        name="Cooldown",
        icon="mdi:timer-sand",
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and "cooldownEnabled" in entity.data
            and "cooldownValue" in entity.data
            and entity.data.get("isAdmin") is True
            and entity.data.get("cooldownSupported") is True
            and entity.data.get("supportPirCooldown") is True
        ),
        value_fn=data_bool("cooldownEnabled"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_device_call",
        data_key="deviceCallToggleOn",
        addx_key="deviceCallToggleOn",
        name="Device Call",
        icon="mdi:phone",
        exists_fn=has_supported_data("deviceCallToggleOn", "supportDeviceCall"),
        value_fn=data_bool("deviceCallToggleOn"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_ding_dong",
        data_key="mechanicalDingDongSwitch",
        addx_key="mechanicalDingDongSwitch",
        name="Mechanical Ding-Dong",
        icon="mdi:bell-ring",
        exists_fn=has_supported_data(
            "mechanicalDingDongSwitch", "supportMechanicalDingDong"
        ),
        value_fn=data_bool("mechanicalDingDongSwitch"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_motion_tracking",
        data_key="motionTrack",
        addx_key="motionTrack",
        name="Motion Tracking",
        icon="mdi:axis-arrow",
        exists_fn=has_supported_data("motionTrack", "supportMotionTrack"),
        value_fn=data_bool("motionTrack"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_voice_volume",
        data_key="voiceVolumeSwitch",
        addx_key="voiceVolumeSwitch",
        name="Voice Volume",
        icon="mdi:volume-high",
        exists_fn=has_supported_data("voiceVolumeSwitch", "supportVoiceVolume"),
        value_fn=data_bool("voiceVolumeSwitch"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_live_audio",
        data_key="liveAudioToggleOn",
        addx_key="audio.liveAudioToggleOn",
        name="Live Audio",
        icon="mdi:volume-high",
        exists_fn=has_apk_default_supported_data(
            "liveAudioToggleOn", "supportLiveAudio"
        ),
        value_fn=data_bool("liveAudioToggleOn"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_recording_audio",
        data_key="recordingAudioToggleOn",
        addx_key="audio.recordingAudioToggleOn",
        name="Recording Audio",
        icon="mdi:microphone",
        exists_fn=has_apk_default_supported_data(
            "recordingAudioToggleOn", "supportRecordingAudio"
        ),
        value_fn=data_bool("recordingAudioToggleOn"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_auto_power_on",
        data_key="chargeAutoPowerOnSwitch",
        addx_key="chargeAutoPowerOnSwitch",
        name="Auto Power-On",
        icon="mdi:battery-sync",
        exists_fn=has_supported_data(
            "chargeAutoPowerOnSwitch", "supportChargeAutoPowerOn"
        ),
        value_fn=data_bool("chargeAutoPowerOnSwitch"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_white_light",
        data_key="whiteLightScintillation",
        addx_key="whiteLightScintillation",
        name="White Light",
        icon="mdi:spotlight-beam",
        exists_fn=has_supported_data("whiteLightScintillation", "supportLight"),
        value_fn=data_bool("whiteLightScintillation"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_alarm_when_removed",
        data_key="alarmWhenRemoveToggleOn",
        addx_key="doorbell.alarmWhenRemoveToggleOn",
        name="Alarm When Removed",
        icon="mdi:bell-alert",
        exists_fn=has_supported_data("alarmWhenRemoveToggleOn", "supportDoorBellAlarm"),
        value_fn=data_bool("alarmWhenRemoveToggleOn"),
    ),
    XSenseSwitchEntityDescription(
        key="camera_sleep",
        data_key="deviceStatus",
        addx_key="sleep.dormancySwitch",
        name="Camera Sleep",
        icon="mdi:power-sleep",
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and entity.data.get("isAdmin") is True
            and entity.data.get("supportSleep") is True
            and "deviceStatus" in entity.data
        ),
        value_fn=lambda entity: entity.data.get("deviceStatus") == 3,
    ),
    *(
        XSenseSwitchEntityDescription(
            key=f"camera_ai_notification_{event_type}",
            data_key=f"aiNotification{_camel_suffix(event_type)}",
            addx_key=f"ai_notification.{event_type}",
            name=_ai_notification_name(event_type),
            icon="mdi:bell-badge",
            exists_fn=has_camera_ai_notification(event_type),
            value_fn=optional_data_bool(f"aiNotification{_camel_suffix(event_type)}"),
        )
        for event_type in CAMERA_AI_NOTIFICATION_TYPES
    ),
    *(
        XSenseSwitchEntityDescription(
            key=f"camera_ai_assistant_{event_object}",
            data_key=f"aiAssistant{_camel_suffix(event_object)}",
            addx_key=f"ai_assistant.{event_object}",
            name=_ai_assistant_name(event_object),
            icon="mdi:brain",
            exists_fn=has_camera_ai_assistant(event_object),
            value_fn=optional_data_bool(f"aiAssistant{_camel_suffix(event_object)}"),
        )
        for event_object in CAMERA_AI_ASSISTANT_TYPES
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the X-Sense switch entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    seen_entity_ids: set[str] = set()
    platform = entity_platform.current_platform.get()
    if platform is not None:
        platform.async_register_entity_service(
            "query_light_schedules",
            {},
            "async_query_light_schedules",
        )
        platform.async_register_entity_service(
            "create_light_schedule",
            LIGHT_SCHEDULE_CREATE_SCHEMA,
            "async_create_light_schedule",
        )
        platform.async_register_entity_service(
            "update_light_schedule",
            LIGHT_SCHEDULE_UPDATE_SCHEMA,
            "async_update_light_schedule",
        )
        platform.async_register_entity_service(
            "rename_light_schedule",
            LIGHT_SCHEDULE_RENAME_SCHEMA,
            "async_rename_light_schedule",
        )
        platform.async_register_entity_service(
            "delete_light_schedule",
            LIGHT_SCHEDULE_DELETE_SCHEMA,
            "async_delete_light_schedule",
        )
        platform.async_register_entity_service(
            "query_light_groups",
            {},
            "async_query_light_groups",
        )
        platform.async_register_entity_service(
            "create_light_group",
            LIGHT_GROUP_CREATE_SCHEMA,
            "async_create_light_group",
        )
        platform.async_register_entity_service(
            "rename_light_group",
            LIGHT_GROUP_RENAME_SCHEMA,
            "async_rename_light_group",
        )
        platform.async_register_entity_service(
            "update_light_group_timer",
            LIGHT_GROUP_TIMER_SCHEMA,
            "async_update_light_group_timer",
        )
        platform.async_register_entity_service(
            "bind_light_group",
            LIGHT_GROUP_BIND_SCHEMA,
            "async_bind_light_group",
        )
        platform.async_register_entity_service(
            "delete_light_group",
            LIGHT_GROUP_DELETE_SCHEMA,
            "async_delete_light_group",
        )
        platform.async_register_entity_service(
            "remove_light_group_devices",
            LIGHT_GROUP_REMOVE_DEVICES_SCHEMA,
            "async_remove_light_group_devices",
        )

    for station in coordinator_stations(coordinator).values():
        seen_entity_ids.add(station.entity_id)
        devices.extend(
            XSenseSwitchEntity(coordinator, station, description)
            for description in SWITCHES
            if description.exists_fn(station)
        )

    for dev in coordinator_devices(coordinator).values():
        if dev.entity_id in seen_entity_ids:
            continue
        devices.extend(
            XSenseSwitchEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in SWITCHES
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseSwitchEntity(XSenseEntity, SwitchEntity):
    """Switches for X-Sense settings."""

    entity_description: XSenseSwitchEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseSwitchEntityDescription,
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
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        entity = self._current_entity()
        if entity is None:
            return None

        return self.entity_description.value_fn(entity)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return cached light schedule data for schedule-capable switches."""
        entity = self._current_entity()
        if (
            entity is None
            or self.entity_description.data_key != "on"
        ):
            return None
        attrs = {}
        if "lightSchedules" in entity.data:
            attrs["light_schedules"] = entity.data["lightSchedules"]
        if "lightGroups" in entity.data:
            attrs["light_groups"] = entity.data["lightGroups"]
        return attrs or None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the X-Sense setting."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the X-Sense setting."""
        await self._async_set_state(False)

    async def async_query_light_schedules(self) -> None:
        """Query and cache SBS50 light schedules from the APK schedule API."""
        entity = self._light_schedule_entity()
        schedules = await self.coordinator.xsense.query_light_schedules(entity)
        entity.data["lightSchedules"] = _light_schedule_list(schedules)
        self.coordinator.async_update_listeners()

    async def async_create_light_schedule(
        self,
        name: str,
        start_time: str,
        end_time: str,
        week_days: list[str],
        enabled: bool = True,
        time_zone: str | None = None,
    ) -> None:
        """Create an SBS50 light schedule using the APK schedule API."""
        entity = self._light_schedule_entity()
        await self.coordinator.xsense.create_light_schedule(
            entity,
            name=name,
            start_time=_schedule_time(start_time),
            end_time=_schedule_time(end_time),
            week_days=_schedule_week_days(week_days),
            enabled=enabled,
            time_zone=self._schedule_time_zone(time_zone),
        )
        self.coordinator.async_update_listeners()

    async def async_update_light_schedule(
        self,
        schedule_id: str,
        start_time: str,
        end_time: str,
        week_days: list[str],
        enabled: bool = True,
        time_zone: str | None = None,
    ) -> None:
        """Update an SBS50 light schedule using the APK schedule API."""
        entity = self._light_schedule_entity()
        await self.coordinator.xsense.update_light_schedule(
            entity,
            schedule_id=schedule_id,
            start_time=_schedule_time(start_time),
            end_time=_schedule_time(end_time),
            week_days=_schedule_week_days(week_days),
            enabled=enabled,
            time_zone=self._schedule_time_zone(time_zone),
        )
        self.coordinator.async_update_listeners()

    async def async_rename_light_schedule(self, schedule_id: str, name: str) -> None:
        """Rename an SBS50 light schedule using the APK schedule API."""
        entity = self._light_schedule_entity()
        await self.coordinator.xsense.rename_light_schedule(
            entity, schedule_id=schedule_id, name=name
        )
        self.coordinator.async_update_listeners()

    async def async_delete_light_schedule(self, schedule_id: str) -> None:
        """Delete an SBS50 light schedule using the APK schedule API."""
        entity = self._light_schedule_entity()
        await self.coordinator.xsense.delete_light_schedule(
            entity, schedule_id=schedule_id
        )
        self.coordinator.async_update_listeners()

    async def async_query_light_groups(self) -> None:
        """Query and cache SBS50 light groups from the APK group API."""
        entity = self._light_group_entity()
        groups = await self.coordinator.xsense.query_light_groups(entity)
        entity.data["lightGroups"] = _light_group_list(groups)
        self.coordinator.async_update_listeners()

    async def async_create_light_group(self, name: str) -> None:
        """Create an SBS50 light group using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.create_light_group(entity, name=name)
        self.coordinator.async_update_listeners()

    async def async_rename_light_group(self, group_id: str, name: str) -> None:
        """Rename an SBS50 light group using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.rename_light_group(
            entity, group_id=group_id, name=name
        )
        self.coordinator.async_update_listeners()

    async def async_update_light_group_timer(
        self, group_id: str, timer: str, value: str
    ) -> None:
        """Update an SBS50 light group timer using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.update_light_group_timer(
            entity, group_id=group_id, data_key=timer, value=value
        )
        self.coordinator.async_update_listeners()

    async def async_bind_light_group(self, name: str, device_ids: list[str]) -> None:
        """Add SBS50 light devices to a group using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.bind_light_group(
            entity,
            name=name,
            device_ids=_non_empty_strings(device_ids, "device_ids"),
        )
        self.coordinator.async_update_listeners()

    async def async_delete_light_group(self, group_id: str) -> None:
        """Delete an SBS50 light group using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.delete_light_group(entity, group_id=group_id)
        self.coordinator.async_update_listeners()

    async def async_remove_light_group_devices(self, device_ids: list[str]) -> None:
        """Remove SBS50 light devices from their group using the APK group API."""
        entity = self._light_group_entity()
        await self.coordinator.xsense.remove_light_group_devices(
            entity, device_ids=_non_empty_strings(device_ids, "device_ids")
        )
        self.coordinator.async_update_listeners()

    def _light_schedule_entity(self) -> Entity:
        """Return the current light entity or raise for unsupported switches."""
        return self._sbs50_light_power_entity("light schedule services")

    def _light_group_entity(self) -> Entity:
        """Return the current SBS50 light/group entity for group services."""
        return self._sbs50_light_power_entity("light group services")

    def _sbs50_light_power_entity(self, service_name: str) -> Entity:
        """Return the current SBS50 light power entity or raise if unsupported."""
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")
        if self.entity_description.data_key != "on" or getattr(
            entity, "entity_type", None
        ) != EntityType.LIGHT:
            raise HomeAssistantError(
                f"X-Sense {service_name} require a light power switch"
            )
        station = getattr(entity, "station", None)
        if not station or station.type != "SBS50":
            raise HomeAssistantError(f"X-Sense {service_name} require an SBS50 station")
        if not getattr(entity, "entity_id", None) or not getattr(
            station, "entity_id", None
        ):
            raise HomeAssistantError(f"X-Sense {service_name} IDs are missing")
        return entity

    def _schedule_time_zone(self, time_zone: str | None) -> str:
        """Return the supplied or Home Assistant configured timezone."""
        return time_zone or self.coordinator.hass.config.time_zone

    async def _async_set_state(self, enabled: bool) -> None:
        """Write the switch state through the X-Sense device settings shadow."""
        xsense = self.coordinator.xsense
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        station = getattr(entity, "station", entity)
        if self.entity_description.data_key == "on":
            await xsense.update_light_power(entity, enabled)
            entity.data[self.entity_description.data_key] = enabled
            self.coordinator.async_update_listeners()
            return

        if is_camera_entity(entity) and self.entity_description.addx_key:
            if self.entity_description.addx_key == "cooldown.userEnable":
                await xsense.update_camera_cooldown(
                    entity,
                    user_enable=enabled,
                    value=int(entity.data["cooldownValue"]),
                )
                self.coordinator.async_update_listeners()
                return

            if self.entity_description.addx_key.startswith("audio."):
                await xsense.update_camera_audio(
                    entity,
                    **{
                        self.entity_description.addx_key.removeprefix("audio."): enabled
                    },
                )
                entity.data[self.entity_description.data_key] = enabled
                self.coordinator.async_update_listeners()
                return

            if self.entity_description.addx_key.startswith("doorbell."):
                await xsense.update_camera_doorbell_config(
                    entity,
                    **{
                        self.entity_description.addx_key.removeprefix(
                            "doorbell."
                        ): enabled
                    },
                )
                entity.data[self.entity_description.data_key] = enabled
                self.coordinator.async_update_listeners()
                return

            if self.entity_description.addx_key.startswith("ai_notification."):
                await xsense.update_camera_ai_notification(
                    entity,
                    self.entity_description.addx_key.removeprefix(
                        "ai_notification."
                    ),
                    enabled,
                )
                self.coordinator.async_update_listeners()
                return

            if self.entity_description.addx_key.startswith("ai_assistant."):
                await xsense.update_camera_ai_assistant(
                    entity,
                    self.entity_description.addx_key.removeprefix("ai_assistant."),
                    enabled,
                )
                self.coordinator.async_update_listeners()
                return

            if self.entity_description.addx_key == "sleep.dormancySwitch":
                await xsense.update_camera_sleep(entity, enabled)
                self.coordinator.async_update_listeners()
                return

            value = _camera_config_write_value(
                self.entity_description.addx_key, enabled
            )
            await xsense.update_camera_config(
                entity, **{self.entity_description.addx_key: value}
            )
            entity.data[self.entity_description.data_key] = enabled
            self.coordinator.async_update_listeners()
            return

        if self.entity_description.data_key == "warnIsOpen":
            await xsense.update_co_pre_alarm(entity, enabled=enabled)
            entity.data[self.entity_description.data_key] = enabled
            self.coordinator.async_update_listeners()
            return

        if self.entity_description.light_on_event is not None:
            await xsense.update_light_setting(
                entity,
                self.entity_description.data_key,
                self.entity_description.write_value_fn(enabled),
                on_event=self.entity_description.light_on_event,
            )
            entity.data[self.entity_description.data_key] = enabled
            self.coordinator.async_update_listeners()
            return

        desired = {
            "deviceSN": entity.sn,
            "shadow": "infoDev",
            "stationSN": station.sn,
            "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "userId": xsense.userid,
            self.entity_description.data_key: self.entity_description.write_value_fn(
                enabled
            ),
        }
        topic = entity_topic(entity)

        await xsense.do_thing(station, topic, {"state": {"desired": desired}})
        entity.data[self.entity_description.data_key] = enabled
        if self.entity_description.read_key:
            entity.data[self.entity_description.read_key] = enabled
        self.coordinator.async_update_listeners()


def _schedule_time(value: str) -> str:
    """Return an APK schedule time in HHMM form."""
    text = str(value).strip()
    if ":" in text:
        hour, minute = text.split(":", 1)
        text = f"{hour.zfill(2)}{minute.zfill(2)}"
    if len(text) != 4 or not text.isdigit():
        raise HomeAssistantError("X-Sense schedule time must be HH:MM or HHMM")
    hour = int(text[:2])
    minute = int(text[2:])
    if hour > 23 or minute > 59:
        raise HomeAssistantError("X-Sense schedule time is out of range")
    return text


def _schedule_week_days(values: list[str]) -> list[str]:
    """Return APK weekday values, where 1 is Sunday and 7 is Saturday."""
    result = [str(value).strip() for value in values]
    if not result:
        raise HomeAssistantError("X-Sense schedule must include at least one weekday")
    invalid = [value for value in result if value not in {"1", "2", "3", "4", "5", "6", "7"}]
    if invalid:
        raise HomeAssistantError("X-Sense schedule weekdays must be 1 through 7")
    return result


def _light_schedule_list(value) -> list:
    """Return a normalized schedule list from the APK query response."""
    if isinstance(value, dict):
        data = value.get("schedList") or value.get("schedule") or value.get("list")
        return data if isinstance(data, list) else []
    return value if isinstance(value, list) else []


def _light_group_list(value) -> list:
    """Return a normalized group list from the APK query response."""
    if isinstance(value, dict):
        data = value.get("groupList") or value.get("groups") or value.get("list")
        if data is None and isinstance(value.get("reData"), dict):
            data = value["reData"].get("groupList")
        return data if isinstance(data, list) else []
    return value if isinstance(value, list) else []


def _non_empty_strings(values: list[str], field_name: str) -> list[str]:
    """Return stripped non-empty strings for service list fields."""
    result = [str(value).strip() for value in values if str(value).strip()]
    if not result:
        raise HomeAssistantError(f"X-Sense {field_name} must include at least one ID")
    return result
