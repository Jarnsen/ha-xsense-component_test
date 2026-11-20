"""Support for xsense binary sensors."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NON_ENTITY_DIAGNOSTIC_BINARY_SENSOR_KEYS
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_stations,
    device_station_id,
    setup_dynamic_entities,
)
from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.device import Device
from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType, entities
from .python_xsense.station import Station

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True, frozen=True)
class XSenseBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes XSense binary-sensor entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True
    value_fn: Callable[[Entity], bool | None]


ALARM_DEVICE_CLASS_BY_TYPE = {
    "SC": BinarySensorDeviceClass.SMOKE,
    "XP": BinarySensorDeviceClass.SMOKE,
    "XS": BinarySensorDeviceClass.SMOKE,
    "XC": BinarySensorDeviceClass.CO,
    "SWS": BinarySensorDeviceClass.MOISTURE,
    "SDS": BinarySensorDeviceClass.DOOR,
    "SMS": BinarySensorDeviceClass.MOTION,
    "SMA": BinarySensorDeviceClass.OPENING,
    "XH": BinarySensorDeviceClass.HEAT,
}

LIFE_END_STATUS_DEVICE_TYPES = frozenset(
    {
        "CB0T-3B", "CB0T-4B", "LP/R-SCA(VL)-0G", "W/R-SCA(VL)-0G",
        # CO, combo, and smoke detector models from the APK device map.
        "CB0Z-3S",
        "LP/N-SA-0B",
        "LP/N-SCA-0A",
        "SC01-MN",
        "SC01-MR",
        "SC06-WX",
        "SC07-MR",
        "SC07-WX",
        "SC07-iA",
        "SD11-MR",
        "SD19-MN",
        "SK0Z-3S",
        "XC01-M",
        "XC04-WX",
        "XC0C-MR",
        "XC0C-iA",
        "XC0C-iR",
        "XC0M-iR",
        "XP02S-MR",
        "XP0A-MR",
        "XP0A-iR",
        "XP0H-MR",
        "XP0H-iR",
        "XP0J-iA",
        "XP0P-MR",
        "XP0S-iA",
        "XP0T-iA",
        "XP0V-iA",
        "XP0W-iA",
        "XR0A-iR",
        "XS01-M",
        "XS01-WX",
        "XS03-WX",
        "XS03-iWX",
        "XS0AA-iA",
        "XS0AB-iA",
        "XS0B-MR",
        "XS0B-iR",
        "XS0D-MR",
        "XS0E-iR",
        "XS0F-PMA",
        "XS0R-iA",
        "XS0X-MN",
    }
)

ALARM_STATUS_DEVICE_TYPES = frozenset(
    {
        "CB0T-3B", "CB0T-4B", "LP/R-SCA(VL)-0G", "W/R-SCA(VL)-0G",
        "CB0Z-3S",
        "LP/N-SA-0B",
        "LP/N-SCA-0A",
        "SAL100",
        "SAL51",
        "SBS50",
        "SC01-MN",
        "SC01-MR",
        "SC06-WX",
        "SC07-MR",
        "SC07-WX",
        "SC07-iA",
        "SD11-MR",
        "SD19-MN",
        "SDA51",
        "SDS0A",
        "SK0Z-3S",
        "SKP0A",
        "SMA0A",
        "SMA51",
        "SMS0A",
        "STH0A",
        "STH0B",
        "STH51",
        "SWS0A",
        "SWS51",
        "XC01-M",
        "XC04-WX",
        "XC0C-MR",
        "XC0C-iA",
        "XC0C-iR",
        "XC0M-iR",
        "XH02-M",
        "XP02S-MR",
        "XP0A-MR",
        "XP0A-iR",
        "XP0H-MR",
        "XP0H-iR",
        "XP0J-iA",
        "XP0P-MR",
        "XP0S-iA",
        "XP0T-iA",
        "XP0V-iA",
        "XP0W-iA",
        "XR0A-iR",
        "XS01-M",
        "XS01-WX",
        "XS03-WX",
        "XS03-iWX",
        "XS0AA-iA",
        "XS0AB-iA",
        "XS0B-MR",
        "XS0B-iR",
        "XS0D-MR",
        "XS0E-iR",
        "XS0F-PMA",
        "XS0R-iA",
        "XS0X-MN",
    }
)

MUTE_STATUS_DEVICE_TYPES = frozenset(
    {
        "CB0T-3B", "CB0T-4B", "LP/R-SCA(VL)-0G", "W/R-SCA(VL)-0G",
        "CB0Z-3S",
        "LP/N-SA-0B",
        "LP/N-SCA-0A",
        "SAL100",
        "SAL51",
        "SC01-MN",
        "SC01-MR",
        "SC06-WX",
        "SC07-MR",
        "SC07-WX",
        "SC07-iA",
        "SD11-MR",
        "SD19-MN",
        "SK0Z-3S",
        "SWS0A",
        "SWS51",
        "XC01-M",
        "XC04-WX",
        "XC0C-MR",
        "XC0C-iA",
        "XC0C-iR",
        "XC0M-iR",
        "XH02-M",
        "XP02S-MR",
        "XP0A-MR",
        "XP0A-iR",
        "XP0H-MR",
        "XP0H-iR",
        "XP0J-iA",
        "XP0P-MR",
        "XP0S-iA",
        "XP0T-iA",
        "XP0V-iA",
        "XP0W-iA",
        "XS01-M",
        "XS01-WX",
        "XS03-WX",
        "XS03-iWX",
        "XS0AA-iA",
        "XS0AB-iA",
        "XS0B-MR",
        "XS0B-iR",
        "XS0D-MR",
        "XS0E-iR",
        "XS0F-PMA",
        "XS0R-iA",
        "XS0X-MN",
    }
)

# APK 1400 handlers C0876k, C0877l, O, and P use muteStatus 1-3 for
# silenced alarms and 4+ for alarms that are still sounding.
CODED_MUTE_STATUS_DEVICE_TYPES = frozenset(
    {
        "CB0T-3B", "CB0T-4B", "LP/R-SCA(VL)-0G", "W/R-SCA(VL)-0G",
        "CB0Z-3S",
        "LP/N-SCA-0A",
        "SC01-MN",
        "SC01-MR",
        "SC06-WX",
        "SC07-MR",
        "SC07-WX",
        "SC07-iA",
        "XP0A-MR",
        "XP0A-iR",
        "XP0H-MR",
        "XP0H-iR",
        "XP0J-iA",
        "XP0P-MR",
        "XP0S-iA",
        "XP0T-iA",
        "XP0V-iA",
        "XP0W-iA",
    }
)

# The remaining detector handlers expose an alarm as silenced only while the
# alarm is active and muteStatus is 0.
ZERO_CODE_MUTE_STATUS_DEVICE_TYPES = MUTE_STATUS_DEVICE_TYPES.difference(
    CODED_MUTE_STATUS_DEVICE_TYPES,
)

COMMAND_ONLY_MUTE_STATUS_DEVICE_TYPES = frozenset({"SMA0A", "SMA51"})


def alarm_device_class(entity: Entity) -> BinarySensorDeviceClass | None:
    """Return the Home Assistant device class for an XSense alarm state."""
    if entities.get(entity.type, {}).get("type") == EntityType.COMBI:
        # The normalized aggregate flag cannot distinguish smoke from CO.
        return None
    for model_prefix, device_class in ALARM_DEVICE_CLASS_BY_TYPE.items():
        if entity.type.startswith(model_prefix):
            return device_class
    return None


def has_alarm_status(entity: Entity) -> bool:
    """Return if an XSense entity should expose an alarm status sensor."""
    if entity.type == "XCG0A-iA":
        return False
    return "alarmStatus" in entity.data or entity.type in ALARM_STATUS_DEVICE_TYPES


def has_mute_status(entity: Entity) -> bool:
    """Return if an X-Sense entity should expose mute status."""
    if entity.type in COMMAND_ONLY_MUTE_STATUS_DEVICE_TYPES:
        return False
    return (
        "muteStatus" in entity.data
        or "mute" in entity.data
        or entity.type in MUTE_STATUS_DEVICE_TYPES
    )


def mute_status(entity: Entity) -> bool | None:
    """Return the model-specific silence state used by APK 1400."""
    raw_value = entity.data.get("muteStatus")

    model = str(getattr(entity, "type", "") or "")
    if raw_value not in (None, "") and model in MUTE_STATUS_DEVICE_TYPES:
        alarm_active = boolean_state(entity.data.get("alarmStatus"))
        if alarm_active is False:
            return False
        if alarm_active is None:
            return None

        code = status_code(raw_value)
        if code is None:
            return None
        if model in CODED_MUTE_STATUS_DEVICE_TYPES:
            return 1 <= code <= 3
        if model in ZERO_CODE_MUTE_STATUS_DEVICE_TYPES:
            return code == 0

    fallback = entity.data.get("mute")
    if fallback in (None, ""):
        fallback = raw_value
    return boolean_state(fallback)


def status_code(value) -> int | None:
    """Return an integer APK status code without applying boolean semantics."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def alarm_silence_status(
    entity: Entity, alarm_key: str, mute_key: str
) -> bool | None:
    """Return APK silence/remind-later state for a specific active alarm."""
    alarm_active = boolean_state(entity.data.get(alarm_key))
    if alarm_active is False:
        return False
    if alarm_active is None:
        return None
    code = status_code(entity.data.get(mute_key))
    return code in {1, 2} if code is not None else None


def has_life_end_status(entity: Entity) -> bool:
    """Return if an X-Sense detector can report end-of-life status."""
    model = str(getattr(entity, "type", "") or "").strip()
    data = getattr(entity, "data", {}) or {}
    return "isLifeEnd" in data or model in LIFE_END_STATUS_DEVICE_TYPES


def life_end_status(entity: Entity) -> bool | None:
    """Return the APK end-of-life state for a supported detector."""
    data = getattr(entity, "data", {}) or {}
    if "isLifeEnd" in data:
        return boolean_state(data["isLifeEnd"])

    model = str(getattr(entity, "type", "") or "").strip()
    if model in LIFE_END_STATUS_DEVICE_TYPES:
        return False
    return None


def alarm_status(entity: Entity) -> bool | None:
    """Return the reported alarm status, or unknown before the first report."""
    if "alarmStatus" not in entity.data:
        return None
    return boolean_state(entity.data["alarmStatus"])


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


def data_bool(key: str) -> Callable[[Entity], bool | None]:
    """Return a value function for a boolean X-Sense data key."""
    return lambda entity: boolean_state(entity.data.get(key))


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for a X-Sense data key."""
    return lambda entity: key in entity.data


def has_camera_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for an IPC camera data key."""
    return lambda entity: is_camera_entity(entity) and key in entity.data


def has_motion_detection(entity: Entity) -> bool:
    """Return if an entity can expose regular motion detection state."""
    if is_camera_entity(entity):
        return True
    return "isMoved" in entity.data


def motion_detection_value(entity: Entity) -> bool | None:
    """Return motion state, defaulting supported cameras to idle before events."""
    if is_camera_entity(entity):
        return boolean_state(entity.data.get("cameraMotionDetected", False))
    return boolean_state(entity.data.get("isMoved"))


def _xcg0a_alarm(entity: Entity, *, gas: bool) -> bool | None:
    """Decode APK 7358's independent gas and CO home card indicators."""
    alarm = status_code(entity.data.get("alarmStatus"))
    mute = status_code(entity.data.get("muteStatus"))
    if alarm is None:
        return None
    if alarm == 5:
        return True
    return (alarm == 4 and mute in {0, 7, 8}) if gas else (alarm == 2 and mute in {0, 5})


def _xcg_low_co_warning(entity: Entity) -> bool | None:
    """Mirror the app's low-CO warning indicator, not its setting."""
    warning = status_code(entity.data.get("warnLong"))
    if warning not in {0, 1}:
        return None
    alarm = status_code(entity.data.get("alarmStatus"))
    mute = status_code(entity.data.get("muteStatus"))
    # Unlike the gas-presence indicator, the APK excludes silenced gas here.
    active_alarm = alarm == 5 or (alarm, mute) in {
        (2, 0), (2, 5), (4, 0), (4, 8), (1, 4), (3, 6),
    }
    return warning == 1 and entity.online is True and not active_alarm


_ALL_SENSORS: tuple[XSenseBinarySensorEntityDescription, ...] = (
    XSenseBinarySensorEntityDescription(
        key="low_co_warning",
        translation_key="low_co_warning",
        icon="mdi:molecule-co",
        exists_fn=lambda entity: entity.type == "XCG0A-iA" and "warnLong" in entity.data,
        value_fn=_xcg_low_co_warning,
    ),
    XSenseBinarySensorEntityDescription(
        key="gas_alarm_status",
        device_class=BinarySensorDeviceClass.GAS,
        exists_fn=lambda entity: entity.type == "XCG0A-iA",
        value_fn=lambda entity: _xcg0a_alarm(entity, gas=True),
    ),
    XSenseBinarySensorEntityDescription(
        key="co_alarm_status",
        device_class=BinarySensorDeviceClass.CO,
        exists_fn=lambda entity: entity.type == "XCG0A-iA",
        value_fn=lambda entity: _xcg0a_alarm(entity, gas=False),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_status",
        translation_key="alarm_status",
        icon="mdi:alarm-light",
        exists_fn=has_alarm_status,
        value_fn=alarm_status,
    ),
    XSenseBinarySensorEntityDescription(
        key="mute_status",
        translation_key="mute_status",
        icon="mdi:alarm-light-off",
        exists_fn=has_mute_status,
        value_fn=mute_status,
    ),
    XSenseBinarySensorEntityDescription(
        key="activate",
        translation_key="activate",
        icon="mdi:bell-ring",
        exists_fn=lambda entity: "activate" in entity.data,
        value_fn=lambda entity: boolean_state(entity.data.get("activate")),
    ),
    XSenseBinarySensorEntityDescription(
        key="ac_break",
        translation_key="ac_break",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("acBreak"),
        value_fn=data_bool("acBreak"),
    ),
    XSenseBinarySensorEntityDescription(
        key="battery_end_of_use",
        translation_key="battery_end_of_use",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("bEndUse"),
        value_fn=data_bool("bEndUse"),
    ),
    XSenseBinarySensorEntityDescription(
        key="is_life_end",
        translation_key="is_life_end",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_life_end_status,
        value_fn=life_end_status,
    ),
    XSenseBinarySensorEntityDescription(
        key="armed",
        translation_key="armed",
        icon="mdi:shield-check",
        exists_fn=has_data("isArmed"),
        value_fn=data_bool("isArmed"),
    ),
    XSenseBinarySensorEntityDescription(
        key="moved",
        translation_key="moved",
        device_class=BinarySensorDeviceClass.MOTION,
        exists_fn=has_motion_detection,
        value_fn=motion_detection_value,
    ),
    XSenseBinarySensorEntityDescription(
        key="usb_charge",
        translation_key="usb_charge",
        device_class=BinarySensorDeviceClass.PLUG,
        exists_fn=has_data("usbCharge"),
        value_fn=data_bool("usbCharge"),
    ),
    XSenseBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        exists_fn=has_data("isCharging"),
        value_fn=data_bool("isCharging"),
    ),
    XSenseBinarySensorEntityDescription(
        key="camera_sleeping",
        translation_key="camera_sleeping",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:power-sleep",
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and "deviceStatus" in entity.data
            and entity.data.get("supportSleep") is True
        ),
        value_fn=lambda entity: (
            entity.data.get("deviceStatus") == 3
            if entity.data.get("deviceStatus") is not None
            else None
        ),
    ),
    XSenseBinarySensorEntityDescription(
        key="base_removed",
        translation_key="base_removed",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("baseRemove"),
        value_fn=data_bool("baseRemove"),
    ),
    XSenseBinarySensorEntityDescription(
        key="activated",
        translation_key="activated",
        icon="mdi:bell-ring",
        exists_fn=has_data("isActivate"),
        value_fn=data_bool("isActivate"),
    ),
    XSenseBinarySensorEntityDescription(
        key="fire_drill_active",
        translation_key="fire_drill_active",
        icon="mdi:fire-alert",
        exists_fn=has_data("isFireDrill"),
        value_fn=data_bool("isFireDrill"),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_active",
        translation_key="alarm_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("isAlarm"),
        value_fn=data_bool("isAlarm"),
    ),
    XSenseBinarySensorEntityDescription(
        key="initiative_alarm",
        translation_key="initiative_alarm",
        icon="mdi:alarm-light",
        exists_fn=has_data("initiativeAlarm"),
        value_fn=data_bool("initiativeAlarm"),
    ),
    XSenseBinarySensorEntityDescription(
        key="test_active",
        translation_key="test_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-circle-outline",
        exists_fn=has_data("test"),
        value_fn=data_bool("test"),
    ),
    XSenseBinarySensorEntityDescription(
        key="mute",
        translation_key="mute",
        icon="mdi:volume-off",
        exists_fn=has_data("mute"),
        value_fn=data_bool("mute"),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_sound_enabled",
        translation_key="alarm_sound_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        exists_fn=has_data("alarmSound"),
        value_fn=data_bool("alarmSound"),
    ),
    XSenseBinarySensorEntityDescription(
        key="app_tip_enabled",
        translation_key="app_tip_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message-badge-outline",
        exists_fn=has_data("appTip"),
        value_fn=data_bool("appTip"),
    ),
    XSenseBinarySensorEntityDescription(
        key="schedule_tip_enabled",
        translation_key="schedule_tip_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-alert",
        exists_fn=has_data("scheduleTip"),
        value_fn=data_bool("scheduleTip"),
    ),
    XSenseBinarySensorEntityDescription(
        key="mailbox_schedule_active",
        translation_key="mailbox_schedule_active",
        icon="mdi:calendar-clock",
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.MAILBOX
            and "scheduleStatus" in entity.data
        ),
        value_fn=data_bool("scheduleStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="water_alarm_status",
        translation_key="water_alarm_status",
        device_class=BinarySensorDeviceClass.MOISTURE,
        exists_fn=has_data("waterAlarmStatus"),
        value_fn=data_bool("waterAlarmStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="water_mute_status",
        translation_key="water_mute_status",
        icon="mdi:water-off",
        exists_fn=has_data("waterMuteStatus"),
        value_fn=lambda entity: alarm_silence_status(
            entity, "waterAlarmStatus", "waterMuteStatus"
        ),
    ),
    XSenseBinarySensorEntityDescription(
        key="temperature_alarm_status",
        translation_key="temperature_alarm_status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("tempAlarmStatus"),
        value_fn=data_bool("tempAlarmStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="temperature_mute_status",
        translation_key="temperature_mute_status",
        icon="mdi:thermometer-off",
        exists_fn=has_data("tempMuteStatus"),
        value_fn=lambda entity: alarm_silence_status(
            entity, "tempAlarmStatus", "tempMuteStatus"
        ),
    ),
    XSenseBinarySensorEntityDescription(
        key="timezone_enabled",
        translation_key="timezone_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:map-clock-outline",
        exists_fn=has_data("timeZoneEnabled"),
        value_fn=data_bool("timeZoneEnabled"),
    ),
    XSenseBinarySensorEntityDescription(
        key="timezone_valid",
        translation_key="timezone_valid",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-check-outline",
        exists_fn=has_data("timeZoneValid"),
        value_fn=data_bool("timeZoneValid"),
    ),
    XSenseBinarySensorEntityDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda device: boolean_state(device.data.get("isOpen")),
        exists_fn=lambda device: "isOpen" in device.data,
    ),
)

SENSORS = tuple(
    description
    for description in _ALL_SENSORS
    if description.key not in NON_ENTITY_DIAGNOSTIC_BINARY_SENSOR_KEYS
)

MQTTSensor = XSenseBinarySensorEntityDescription(
    key="connected",
    translation_key="connected",
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:connection",
    exists_fn=lambda entity: isinstance(entity, Station),
    value_fn=lambda entity: False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the xsense binary sensor entry."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def _entities(should_add, discovery_devices) -> list[Device]:
        devices: list[Device] = []
        for station in coordinator_stations(coordinator).values():
            devices.extend(
                XSenseBinarySensorEntity(coordinator, station, description)
                for description in SENSORS
                if description.exists_fn(station) and should_add(station, description.key)
            )
            if should_add(station, MQTTSensor.key):
                devices.append(XSenseMQTTConnectedEntity(coordinator, station, MQTTSensor))

        for dev in discovery_devices.values():
            devices.extend(
                XSenseBinarySensorEntity(
                    coordinator, dev, description, station_id=device_station_id(dev)
                )
                for description in SENSORS
                if description.exists_fn(dev) and should_add(dev, description.key)
            )
        return devices

    setup_dynamic_entities(entry, coordinator, async_add_entities, _entities)


_LOCAL_XS0B_STATES = {
    "alarm_status": ("smokealarm", "Detected", "Cleared"),
    "is_life_end": ("lifeend", "EOL", "Normal"),
}
_LOCAL_SMOKE_MODELS = frozenset({"XS0B-MR", "XS01-M"})


def _local_alarm_state(device: Device, key: str) -> tuple[str, str, str] | None:
    if device.type == "XH02-M" and key == "alarm_status":
        return "heatalarm", "Detected", "Cleared"
    if device.type in _LOCAL_SMOKE_MODELS:
        return _LOCAL_XS0B_STATES.get(key)
    return None


def _local_xs0b_topic(device: Entity | None, key: str) -> str | None:
    if not isinstance(device, Device):
        return None
    station = device.station
    mapping = _local_alarm_state(device, key)
    if station.type != "SBS50" or mapping is None:
        return None
    if not isinstance(station.sn, str) or not re.fullmatch(r"[0-9A-Fa-f]{8}", station.sn):
        return None
    if not isinstance(device.sn, str) or not re.fullmatch(r"[0-9A-Fa-f]{8}", device.sn):
        return None
    node = f"SBS50{station.sn}_{device.sn}"
    attribute = mapping[0]
    return f"homeassistant/binary_sensor/{node}/{node}_{attribute}/state"


class XSenseBinarySensorEntity(XSenseEntity, BinarySensorEntity):
    """Binary sensors for xsense."""

    entity_description: XSenseBinarySensorEntityDescription
    _mqtt_child_state_only = True

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseBinarySensorEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self.entity_description = entity_description
        self._attr_available = False  # This overrides the default
        self._local_state: bool | None = None
        self._local_alarm_at: datetime | None = None
        self._local_topic: str | None = None

        super().__init__(coordinator, entity, station_id)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        topic = _local_xs0b_topic(self._current_entity(), self.entity_description.key)
        if topic is None or "mqtt" not in self.hass.config.components:
            return
        from homeassistant.components import mqtt

        try:
            unsubscribe = await mqtt.async_subscribe(self.hass, topic, self._local_message, qos=1)
        except HomeAssistantError:
            _LOGGER.debug("SBS50 local MQTT subscription unavailable: entity=%s", self.entity_description.key)
            return
        self._local_topic = topic

        def remove_subscription() -> None:
            self._local_topic = None
            self._local_state = None
            unsubscribe()

        self.async_on_remove(remove_subscription)
        self.async_on_remove(
            mqtt.async_subscribe_connection_status(self.hass, self._local_connection)
        )

    @callback
    def _local_connection(self, connected: bool) -> None:
        if not connected and self._local_state is not None:
            self._local_state = None
            self._local_alarm_at = None
            _LOGGER.debug("SBS50 local MQTT disconnected; using cloud: entity=%s", self.entity_description.key)
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._local_alarm_at is not None:
            device = self._current_entity()
            if (
                isinstance(device, Device)
                and self._local_topic == _local_xs0b_topic(device, self.entity_description.key)
                and (clear := device.cloud_alarm_clear_time) is not None
                and self._local_alarm_at < clear <= datetime.now(UTC)
                and self.entity_description.value_fn(device) is False
            ):
                self._local_state = None
                self._local_alarm_at = None
                _LOGGER.debug("SBS50 newer cloud alarm clear recovered local state: model=%s", device.type)
        super()._handle_coordinator_update()

    @callback
    def _local_message(self, message) -> None:
        device = self._current_entity()
        if (
            not isinstance(device, Device)
            or message.retain
            or self._local_topic != message.topic
            or message.topic != _local_xs0b_topic(
                device, self.entity_description.key
            )
        ):
            return
        try:
            payload = json.loads(message.payload)
        except (ValueError, TypeError):
            return
        if not isinstance(payload, dict):
            return
        mapping = _local_alarm_state(device, self.entity_description.key)
        if mapping is None:
            return
        _, on, off = mapping
        status = payload.get("status")
        if status not in (on, off):
            _LOGGER.debug(
                "Ignored SBS50 local MQTT status outside the verified mapping: model=%s field=%s",
                device.type, self.entity_description.key,
            )
            return
        previous = self.is_on
        self._local_state = status == on
        self._local_alarm_at = (
            datetime.now(UTC)
            if self._local_state and self.entity_description.key == "alarm_status"
            else None
        )
        if previous != self.is_on:
            _LOGGER.debug(
                "SBS50 local MQTT state changed: model=%s field=%s active=%s",
                device.type, self.entity_description.key, self._local_state,
            )
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        device = self._current_entity()
        if device is None:
            return None

        cloud_state = self.entity_description.value_fn(device)
        if cloud_state is True or self._local_state is None:
            return cloud_state
        if self._local_topic != _local_xs0b_topic(device, self.entity_description.key):
            return cloud_state
        return self._local_state

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the device class of the binary sensor."""
        if self.entity_description.key != "alarm_status":
            return self.entity_description.device_class

        entity = self._current_entity()
        if entity is None:
            return None

        return alarm_device_class(entity)


class XSenseMQTTConnectedEntity(XSenseBinarySensorEntity):
    """Binary sensors for MQTT connectivity."""

    _mqtt_child_state_only = False

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""

        device = self._current_entity()
        if device is None:
            return None

        if device.online is None:
            return None

        return device.online is True
