"""Support for xsense binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .api.async_xsense import is_camera_entity
from .api.device import Device
from .api.entity import Entity
from .api.station import Station

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


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


def alarm_device_class(entity: Entity) -> BinarySensorDeviceClass | None:
    """Return the Home Assistant device class for an XSense alarm state."""
    for model_prefix, device_class in ALARM_DEVICE_CLASS_BY_TYPE.items():
        if entity.type.startswith(model_prefix):
            return device_class
    return None


def has_alarm_status(entity: Entity) -> bool:
    """Return if an XSense entity should expose an alarm status sensor."""
    return "alarmStatus" in entity.data or alarm_device_class(entity) is not None


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
    return lambda entity: boolean_state(entity.data[key])


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for a X-Sense data key."""
    return lambda entity: key in entity.data


def has_camera_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for an IPC camera data key."""
    return lambda entity: is_camera_entity(entity) and key in entity.data


SENSORS: tuple[XSenseBinarySensorEntityDescription, ...] = (
    XSenseBinarySensorEntityDescription(
        key="is_life_end",
        translation_key="is_life_end",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=lambda entity: "isLifeEnd" in entity.data,
        value_fn=data_bool("isLifeEnd"),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_status",
        translation_key="alarm_status",
        exists_fn=has_alarm_status,
        value_fn=alarm_status,
    ),
    XSenseBinarySensorEntityDescription(
        key="mute_status",
        translation_key="mute_status",
        exists_fn=lambda entity: "muteStatus" in entity.data,
        value_fn=lambda entity: boolean_state(entity.data["muteStatus"]),
    ),
    XSenseBinarySensorEntityDescription(
        key="activate",
        translation_key="activate",
        exists_fn=lambda entity: "activate" in entity.data,
        value_fn=lambda entity: boolean_state(entity.data["activate"]),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_enabled",
        name="Alarm Enabled",
        icon="mdi:bell-check",
        exists_fn=lambda entity: (
            "alarmEnable" in entity.data or "alarmEnabled" in entity.data
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("alarmEnable", entity.data.get("alarmEnabled"))
        ),
    ),
    XSenseBinarySensorEntityDescription(
        key="continued_alarm",
        name="Continued Alarm",
        icon="mdi:bell-plus",
        exists_fn=lambda entity: (
            "continueAlarm" in entity.data or "continuedAlarm" in entity.data
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("continueAlarm", entity.data.get("continuedAlarm"))
        ),
    ),
    XSenseBinarySensorEntityDescription(
        key="ac_break",
        name="AC Break",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("acBreak"),
        value_fn=data_bool("acBreak"),
    ),
    XSenseBinarySensorEntityDescription(
        key="battery_end_of_use",
        name="Battery End of Use",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("bEndUse"),
        value_fn=data_bool("bEndUse"),
    ),
    XSenseBinarySensorEntityDescription(
        key="mail_notice",
        name="Mail Notice",
        icon="mdi:mailbox-up",
        exists_fn=has_data("mailNotice"),
        value_fn=data_bool("mailNotice"),
    ),
    XSenseBinarySensorEntityDescription(
        key="armed",
        name="Armed",
        icon="mdi:shield-check",
        exists_fn=has_data("isArmed"),
        value_fn=data_bool("isArmed"),
    ),
    XSenseBinarySensorEntityDescription(
        key="moved",
        name="Moved",
        device_class=BinarySensorDeviceClass.MOTION,
        exists_fn=has_data("isMoved"),
        value_fn=data_bool("isMoved"),
    ),
    XSenseBinarySensorEntityDescription(
        key="usb_charge",
        name="USB Charging",
        device_class=BinarySensorDeviceClass.PLUG,
        exists_fn=has_data("usbCharge"),
        value_fn=data_bool("usbCharge"),
    ),
    XSenseBinarySensorEntityDescription(
        key="charging",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        exists_fn=has_data("isCharging"),
        value_fn=data_bool("isCharging"),
    ),
    XSenseBinarySensorEntityDescription(
        key="camera_sleeping",
        name="Camera Sleeping",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:power-sleep",
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and "deviceStatus" in entity.data
            and entity.data.get("supportSleep") is True
        ),
        value_fn=lambda entity: entity.data["deviceStatus"] == 3,
    ),
    XSenseBinarySensorEntityDescription(
        key="base_removed",
        name="Base Removed",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("baseRemove"),
        value_fn=data_bool("baseRemove"),
    ),
    XSenseBinarySensorEntityDescription(
        key="activated",
        name="Activated",
        icon="mdi:bell-ring",
        exists_fn=has_data("isActivate"),
        value_fn=data_bool("isActivate"),
    ),
    XSenseBinarySensorEntityDescription(
        key="fire_drill_active",
        name="Fire Drill Active",
        icon="mdi:fire-alert",
        exists_fn=has_data("isFireDrill"),
        value_fn=data_bool("isFireDrill"),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_active",
        name="Alarm Active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("isAlarm"),
        value_fn=data_bool("isAlarm"),
    ),
    XSenseBinarySensorEntityDescription(
        key="initiative_alarm",
        name="Initiative Alarm",
        icon="mdi:alarm-light",
        exists_fn=has_data("initiativeAlarm"),
        value_fn=data_bool("initiativeAlarm"),
    ),
    XSenseBinarySensorEntityDescription(
        key="test_active",
        name="Test Active",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-circle-outline",
        exists_fn=has_data("test"),
        value_fn=data_bool("test"),
    ),
    XSenseBinarySensorEntityDescription(
        key="on",
        name="On",
        icon="mdi:power",
        exists_fn=has_data("on"),
        value_fn=data_bool("on"),
    ),
    XSenseBinarySensorEntityDescription(
        key="mute",
        name="Mute",
        icon="mdi:volume-off",
        exists_fn=has_data("mute"),
        value_fn=data_bool("mute"),
    ),
    XSenseBinarySensorEntityDescription(
        key="await_enabled",
        name="Await Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-sand",
        exists_fn=has_data("awaitEnable"),
        value_fn=data_bool("awaitEnable"),
    ),
    XSenseBinarySensorEntityDescription(
        key="pir_enabled",
        name="PIR Enabled",
        icon="mdi:motion-sensor",
        exists_fn=has_data("pirEnable"),
        value_fn=data_bool("pirEnable"),
    ),
    XSenseBinarySensorEntityDescription(
        key="sunshine_enabled",
        name="Sunshine Enabled",
        icon="mdi:white-balance-sunny",
        exists_fn=has_data("sunshineEnable"),
        value_fn=data_bool("sunshineEnable"),
    ),
    XSenseBinarySensorEntityDescription(
        key="alarm_sound_enabled",
        name="Alarm Sound Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        exists_fn=has_data("alarmSound"),
        value_fn=data_bool("alarmSound"),
    ),
    XSenseBinarySensorEntityDescription(
        key="key_sound_enabled",
        name="Key Sound Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        exists_fn=has_data("keySound"),
        value_fn=data_bool("keySound"),
    ),
    XSenseBinarySensorEntityDescription(
        key="app_tip_enabled",
        name="App Tip Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message-badge-outline",
        exists_fn=has_data("appTip"),
        value_fn=data_bool("appTip"),
    ),
    XSenseBinarySensorEntityDescription(
        key="schedule_tip_enabled",
        name="Schedule Tip Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-alert",
        exists_fn=has_data("scheduleTip"),
        value_fn=data_bool("scheduleTip"),
    ),
    XSenseBinarySensorEntityDescription(
        key="water_alarm_status",
        name="Water Alarm Status",
        device_class=BinarySensorDeviceClass.MOISTURE,
        exists_fn=has_data("waterAlarmStatus"),
        value_fn=data_bool("waterAlarmStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="water_mute_status",
        name="Water Mute Status",
        icon="mdi:water-off",
        exists_fn=has_data("waterMuteStatus"),
        value_fn=data_bool("waterMuteStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="temperature_alarm_status",
        name="Temperature Alarm Status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=has_data("tempAlarmStatus"),
        value_fn=data_bool("tempAlarmStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="temperature_mute_status",
        name="Temperature Mute Status",
        icon="mdi:thermometer-off",
        exists_fn=has_data("tempMuteStatus"),
        value_fn=data_bool("tempMuteStatus"),
    ),
    XSenseBinarySensorEntityDescription(
        key="timezone_enabled",
        name="Time Zone Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=has_data("timeZoneEnabled"),
        value_fn=data_bool("timeZoneEnabled"),
    ),
    XSenseBinarySensorEntityDescription(
        key="timezone_valid",
        name="Time Zone Valid",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=has_data("timeZoneValid"),
        value_fn=data_bool("timeZoneValid"),
    ),
    XSenseBinarySensorEntityDescription(
        key="warning_enabled",
        name="Warning Enabled",
        icon="mdi:alert",
        exists_fn=has_data("warnIsOpen"),
        value_fn=data_bool("warnIsOpen"),
    ),
    XSenseBinarySensorEntityDescription(
        key="chirp_tone_enabled",
        name="Chirp Tone Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        exists_fn=has_data("chirpToneEnable"),
        value_fn=data_bool("chirpToneEnable"),
    ),
    XSenseBinarySensorEntityDescription(
        key="reminder_enabled",
        name="Reminder Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bell-clock",
        exists_fn=has_data("remindOn"),
        value_fn=data_bool("remindOn"),
    ),
    XSenseBinarySensorEntityDescription(
        key="reminder_tone_enabled",
        name="Reminder Tone Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        exists_fn=has_data("remindToneEnable"),
        value_fn=data_bool("remindToneEnable"),
    ),
    XSenseBinarySensorEntityDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        name="Door Sensor",
        value_fn=lambda device: boolean_state(device.data["isOpen"]),
        exists_fn=lambda device: "isOpen" in device.data,
    ),
)

MQTTSensor = XSenseBinarySensorEntityDescription(
    key="connected",
    translation_key="connected",
    entity_category=EntityCategory.DIAGNOSTIC,
    exists_fn=lambda entity: isinstance(entity, Station),
    value_fn=lambda entity: False,
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
            XSenseBinarySensorEntity(coordinator, station, description)
            for description in SENSORS
            if description.exists_fn(station)
        )
        devices.append(XSenseMQTTConnectedEntity(coordinator, station, MQTTSensor))

    for dev in coordinator.data["devices"].values():
        devices.extend(
            XSenseBinarySensorEntity(
                coordinator, dev, description, station_id=dev.station.entity_id
            )
            for description in SENSORS
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseBinarySensorEntity(XSenseEntity, BinarySensorEntity):
    """Binary sensors for xsense."""

    entity_description: XSenseBinarySensorEntityDescription

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

        super().__init__(coordinator, entity, station_id)

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        device = self._current_entity()
        if device is None:
            return None

        return self.entity_description.value_fn(device)

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

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""

        device = self._current_entity()
        if device is None:
            return None

        if device.online is None:
            return None

        return device.online is True
