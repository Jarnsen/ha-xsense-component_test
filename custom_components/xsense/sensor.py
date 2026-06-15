"""Support for xsense sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .api.async_xsense import is_camera_entity
from .api.device import Device
from .api.entity import Entity
from .api.entity_map import EntityType, entities

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, STATE_SIGNAL
from .entity import XSenseEntity


if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


@dataclass(kw_only=True, frozen=True)
class XSenseSensorEntityDescription(SensorEntityDescription):
    """Describes XSense sensor entity."""

    exists_fn: Callable[[Entity], bool] = lambda _: True
    value_fn: Callable[[Entity], StateType | datetime]


def battery_percentage(device: Entity) -> int | None:
    """Return the X-Sense battery level as a whole Home Assistant percentage."""
    value = device.data["batInfo"]
    if value is None:
        return None
    try:
        level = int(value)
    except (TypeError, ValueError):
        return None
    return min(max(round((level * 100) / 3), 0), 100)


def rf_level(device: Entity) -> str | None:
    """Return the X-Sense RF signal level."""
    value = device.data["rfLevel"]
    if value is None:
        return None
    try:
        return STATE_SIGNAL[int(value)]
    except (IndexError, ValueError):
        return None


def data_value(key: str) -> Callable[[Entity], StateType]:
    """Return a value function for a X-Sense data key."""
    return lambda entity: entity.data[key]


def timestamp_value(value) -> datetime | None:
    """Return an aware datetime for X-Sense timestamp payload values."""
    if value in (None, ""):
        return None

    text = str(value)
    if text.isdigit():
        try:
            if len(text) == 14:
                return datetime.strptime(text, "%Y%m%d%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            if len(text) == 13:
                return datetime.fromtimestamp(int(text) / 1000, tz=timezone.utc)
            if len(text) == 10:
                return datetime.fromtimestamp(int(text), tz=timezone.utc)
        except (OSError, ValueError):
            return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, ValueError):
            return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def data_timestamp(key: str) -> Callable[[Entity], datetime | None]:
    """Return a value function for a X-Sense timestamp data key."""
    return lambda entity: timestamp_value(entity.data[key])


def optional_data_timestamp(key: str) -> Callable[[Entity], datetime | None]:
    """Return an optional timestamp value function for late-reporting fields."""
    return lambda entity: timestamp_value(entity.data.get(key))


def self_test_result(entity: Entity) -> str | None:
    """Return a readable self-test result from the X-Sense selftestup report."""
    value = entity.data.get("lastSelfTest")
    if value in (None, ""):
        return "not_run"
    if str(value) == "0":
        return "success"
    return "failed"


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for a X-Sense data key."""
    return lambda entity: key in entity.data


def has_camera_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for an IPC camera data key."""
    return lambda entity: is_camera_entity(entity) and key in entity.data


def has_report_time(entity: Entity) -> bool:
    """Return whether a report timestamp should be exposed as a sensor."""
    return "time" in entity.data and entity.entity_type is not EntityType.BASESTATION


def has_self_test_report(entity: Entity) -> bool:
    """Return whether the entity can report an app-style self-test result."""
    entity_def = entities.get(entity.type, {})
    return "lastSelfTest" in entity.data or any(
        action.get("action") == "test" for action in entity_def.get("actions", [])
    )


SENSORS: tuple[XSenseSensorEntityDescription, ...] = (
    XSenseSensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda entity: "wifiRSSI" in entity.data,
        value_fn=lambda entity: entity.data["wifiRSSI"],
    ),
    XSenseSensorEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda entity: "ssid" in entity.data,
        value_fn=lambda entity: entity.data["ssid"],
    ),
    XSenseSensorEntityDescription(
        key="wifi_sw",
        translation_key="wifi_sw",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda device: "wifi_sw" in device.data,
        value_fn=lambda station: station.data["wifi_sw"],
    ),
    XSenseSensorEntityDescription(
        key="ip",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda device: "ip" in device.data,
        value_fn=lambda device: device.data["ip"],
    ),
    XSenseSensorEntityDescription(
        key="led_brightness",
        name="LED Brightness",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:brightness-6",
        exists_fn=has_data("ledBrt"),
        value_fn=data_value("ledBrt"),
    ),
    XSenseSensorEntityDescription(
        key="await_brightness",
        name="Await Brightness",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:brightness-6",
        exists_fn=has_data("awaitBrightness"),
        value_fn=data_value("awaitBrightness"),
    ),
    XSenseSensorEntityDescription(
        key="trigger_brightness",
        name="Trigger Brightness",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:brightness-6",
        exists_fn=has_data("triggerBrightness"),
        value_fn=data_value("triggerBrightness"),
    ),
    XSenseSensorEntityDescription(
        key="co",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.data["coPpm"],
        exists_fn=lambda device: "coPpm" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="co_peak",
        name="CO Peak",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("coPpmPeak"),
        exists_fn=has_data("coPpmPeak"),
    ),
    XSenseSensorEntityDescription(
        key="co_level",
        name="CO Level",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule-co",
        value_fn=data_value("coLevel"),
        exists_fn=has_data("coLevel"),
    ),
    XSenseSensorEntityDescription(
        key="co_peak_time",
        name="CO Peak Time",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-alert-outline",
        value_fn=data_value("coPpmPeakTime"),
        exists_fn=has_data("coPpmPeakTime"),
    ),
    XSenseSensorEntityDescription(
        key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.data["temperature"],
        exists_fn=lambda device: "temperature" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.data["humidity"],
        exists_fn=lambda device: "humidity" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="temperature_min",
        name="Temperature Minimum",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("tempRangeMin"),
        exists_fn=has_data("tempRangeMin"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_max",
        name="Temperature Maximum",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("tempRangeMax"),
        exists_fn=has_data("tempRangeMax"),
    ),
    XSenseSensorEntityDescription(
        key="humidity_min",
        name="Humidity Minimum",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("humRangeMin"),
        exists_fn=has_data("humRangeMin"),
    ),
    XSenseSensorEntityDescription(
        key="humidity_max",
        name="Humidity Maximum",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("humRangeMax"),
        exists_fn=has_data("humRangeMax"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_unit",
        name="Temperature Unit",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:temperature-celsius",
        value_fn=data_value("tempUnit"),
        exists_fn=has_data("tempUnit"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_adjustment",
        name="Temperature Adjustment",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_value("tAdjust"),
        exists_fn=has_data("tAdjust"),
    ),
    XSenseSensorEntityDescription(
        key="humidity_adjustment",
        name="Humidity Adjustment",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_value("hAdjust"),
        exists_fn=has_data("hAdjust"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_comfort",
        name="Temperature Comfort",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("tComfort"),
        exists_fn=has_data("tComfort"),
    ),
    XSenseSensorEntityDescription(
        key="humidity_comfort",
        name="Humidity Comfort",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("hComfort"),
        exists_fn=has_data("hComfort"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_range",
        name="Temperature Range",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-lines",
        value_fn=data_value("tRange"),
        exists_fn=has_data("tRange"),
    ),
    XSenseSensorEntityDescription(
        key="humidity_range",
        name="Humidity Range",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water-percent",
        value_fn=data_value("hRange"),
        exists_fn=has_data("hRange"),
    ),
    XSenseSensorEntityDescription(
        key="comfort_type",
        name="Comfort Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:home-thermometer-outline",
        value_fn=data_value("comfortType"),
        exists_fn=has_data("comfortType"),
    ),
    XSenseSensorEntityDescription(
        key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=battery_percentage,
        exists_fn=lambda device: "batInfo" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="camera_battery",
        name="Camera Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=data_value("batteryLevel"),
        exists_fn=has_camera_data("batteryLevel"),
    ),
    XSenseSensorEntityDescription(
        key="rf_level",
        translation_key="rf_level",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Signal strength",
        options=STATE_SIGNAL,
        value_fn=rf_level,
        exists_fn=lambda device: "rfLevel" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="wifi_rssi_level",
        name="Wi-Fi RSSI Level",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-strength-2",
        value_fn=data_value("wifiRssiLevel"),
        exists_fn=has_data("wifiRssiLevel"),
    ),
    XSenseSensorEntityDescription(
        key="camera_signal_strength",
        name="Camera Signal Strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_value("signalStrength"),
        exists_fn=has_camera_data("signalStrength"),
    ),
    XSenseSensorEntityDescription(
        key="smoke_edition",
        name="Smoke Edition",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:smoke-detector-variant",
        value_fn=data_value("smokeEdition"),
        exists_fn=has_data("smokeEdition"),
    ),
    XSenseSensorEntityDescription(
        key="standard",
        name="Standard",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:certificate-outline",
        value_fn=data_value("standard"),
        exists_fn=has_data("standard"),
    ),
    XSenseSensorEntityDescription(
        key="alarm_tone",
        name="Alarm Tone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:music-note",
        value_fn=data_value("alarmTone"),
        exists_fn=has_data("alarmTone"),
    ),
    XSenseSensorEntityDescription(
        key="chirp_tone",
        name="Chirp Tone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:music-note",
        value_fn=data_value("chirpTone"),
        exists_fn=has_data("chirpTone"),
    ),
    XSenseSensorEntityDescription(
        key="reminder_tone",
        name="Reminder Tone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:music-note",
        value_fn=data_value("remindTone"),
        exists_fn=has_data("remindTone"),
    ),
    XSenseSensorEntityDescription(
        key="alarm_interval",
        name="Alarm Interval",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
        value_fn=data_value("alarmInterval"),
        exists_fn=has_data("alarmInterval"),
    ),
    XSenseSensorEntityDescription(
        key="reminder_time",
        name="Reminder Time",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bell-clock",
        value_fn=data_value("remindTime"),
        exists_fn=has_data("remindTime"),
    ),
    XSenseSensorEntityDescription(
        key="detection_sensitivity",
        name="Detection Sensitivity",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        value_fn=data_value("detcSens"),
        exists_fn=has_data("detcSens"),
    ),
    XSenseSensorEntityDescription(
        key="sensitivity",
        name="Sensitivity",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        value_fn=data_value("sensitivity"),
        exists_fn=has_data("sensitivity"),
    ),
    XSenseSensorEntityDescription(
        key="check_type",
        name="Check Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:checkbox-marked-circle-outline",
        value_fn=data_value("checkType"),
        exists_fn=has_data("checkType"),
    ),
    XSenseSensorEntityDescription(
        key="pir_time",
        name="PIR Time",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:motion-sensor",
        value_fn=data_value("pirTime"),
        exists_fn=has_data("pirTime"),
    ),
    XSenseSensorEntityDescription(
        key="pir_interval",
        name="PIR Interval",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
        value_fn=data_value("pirInterval"),
        exists_fn=has_data("pirInterval"),
    ),
    XSenseSensorEntityDescription(
        key="pir_sensitivity",
        name="PIR Sensitivity",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        value_fn=data_value("pirSensitivity"),
        exists_fn=has_data("pirSensitivity"),
    ),
    XSenseSensorEntityDescription(
        key="silence_time",
        name="Silence Time",
        icon="mdi:alarm-light-off",
        value_fn=data_value("silenceTime"),
        exists_fn=has_data("silenceTime"),
    ),
    XSenseSensorEntityDescription(
        key="temperature_mute_time",
        name="Temperature Mute Time",
        icon="mdi:thermometer-off",
        value_fn=data_value("tempMuteTime"),
        exists_fn=has_data("tempMuteTime"),
    ),
    XSenseSensorEntityDescription(
        key="water_mute_time",
        name="Water Mute Time",
        icon="mdi:water-off",
        value_fn=data_value("waterMuteTime"),
        exists_fn=has_data("waterMuteTime"),
    ),
    XSenseSensorEntityDescription(
        key="short_warning",
        name="Short Warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-outline",
        value_fn=data_value("warnShort"),
        exists_fn=has_data("warnShort"),
    ),
    XSenseSensorEntityDescription(
        key="short_warning_co",
        name="Short Warning CO",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("warnShortCoPpm"),
        exists_fn=has_data("warnShortCoPpm"),
    ),
    XSenseSensorEntityDescription(
        key="long_warning",
        name="Long Warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
        value_fn=data_value("warnLong"),
        exists_fn=has_data("warnLong"),
    ),
    XSenseSensorEntityDescription(
        key="long_warning_co",
        name="Long Warning CO",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("warnLongCoPpm"),
        exists_fn=has_data("warnLongCoPpm"),
    ),
    XSenseSensorEntityDescription(
        key="warning_period",
        name="Warning Period",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        value_fn=data_value("warnPeriod"),
        exists_fn=has_data("warnPeriod"),
    ),
    XSenseSensorEntityDescription(
        key="alarm_occur",
        name="Alarm Occur",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alarm-light",
        value_fn=data_value("alarmOccur"),
        exists_fn=has_data("alarmOccur"),
    ),
    XSenseSensorEntityDescription(
        key="alarm_source",
        name="Alarm Source",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:source-branch",
        value_fn=data_value("alarmSource"),
        exists_fn=has_data("alarmSource"),
    ),
    XSenseSensorEntityDescription(
        key="re_alarm",
        name="Re-Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alarm-light-outline",
        value_fn=data_value("reAlarm"),
        exists_fn=has_data("reAlarm"),
    ),
    XSenseSensorEntityDescription(
        key="time",
        name="Report Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("time"),
        exists_fn=has_report_time,
    ),
    XSenseSensorEntityDescription(
        key="utc_time",
        name="UTC Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("utcTime"),
        exists_fn=has_data("utcTime"),
    ),
    XSenseSensorEntityDescription(
        key="app_time",
        name="App Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("appTime"),
        exists_fn=has_data("appTime"),
    ),
    XSenseSensorEntityDescription(
        key="test_time",
        name="Test Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("testTime"),
        exists_fn=has_data("testTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_self_test",
        translation_key="last_self_test",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-circle-outline",
        value_fn=self_test_result,
        exists_fn=has_self_test_report,
    ),
    XSenseSensorEntityDescription(
        key="last_self_test_time",
        translation_key="last_self_test_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=optional_data_timestamp("lastSelfTestTime"),
        exists_fn=has_self_test_report,
    ),
    XSenseSensorEntityDescription(
        key="last_motion_time",
        name="Last Motion Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastMotionTime"),
        exists_fn=has_data("lastMotionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_ai_detection",
        name="Last AI Detection",
        icon="mdi:shape-outline",
        value_fn=data_value("lastAiDetection"),
        exists_fn=has_camera_data("lastAiDetection"),
    ),
    XSenseSensorEntityDescription(
        key="last_person_detection_time",
        name="Last Person Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPersonDetectionTime"),
        exists_fn=has_camera_data("lastPersonDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_pet_detection_time",
        name="Last Pet Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPetDetectionTime"),
        exists_fn=has_camera_data("lastPetDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_vehicle_detection_time",
        name="Last Vehicle Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastVehicleDetectionTime"),
        exists_fn=has_camera_data("lastVehicleDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_package_detection_time",
        name="Last Package Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPackageDetectionTime"),
        exists_fn=has_camera_data("lastPackageDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_other_detection_time",
        name="Last Other Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastOtherDetectionTime"),
        exists_fn=has_camera_data("lastOtherDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_vehicle_enter_detection_time",
        name="Last Vehicle Enter Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastVehicleEnterDetectionTime"),
        exists_fn=has_camera_data("lastVehicleEnterDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_vehicle_out_detection_time",
        name="Last Vehicle Exit Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastVehicleOutDetectionTime"),
        exists_fn=has_camera_data("lastVehicleOutDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_vehicle_held_up_detection_time",
        name="Last Vehicle Held Up Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastVehicleHeldUpDetectionTime"),
        exists_fn=has_camera_data("lastVehicleHeldUpDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_package_drop_off_detection_time",
        name="Last Package Drop-Off Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPackageDropOffDetectionTime"),
        exists_fn=has_camera_data("lastPackageDropOffDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_package_pick_up_detection_time",
        name="Last Package Pick-Up Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPackagePickUpDetectionTime"),
        exists_fn=has_camera_data("lastPackagePickUpDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="last_package_exist_detection_time",
        name="Last Package Present Detection Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=optional_data_timestamp("lastPackageExistDetectionTime"),
        exists_fn=has_camera_data("lastPackageExistDetectionTime"),
    ),
    XSenseSensorEntityDescription(
        key="timezone",
        name="Time Zone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:map-clock-outline",
        value_fn=data_value("timeZone"),
        exists_fn=has_data("timeZone"),
    ),
    XSenseSensorEntityDescription(
        key="zone_name",
        name="Zone Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:map-marker-outline",
        value_fn=data_value("zoneName"),
        exists_fn=has_data("zoneName"),
    ),
    XSenseSensorEntityDescription(
        key="location",
        name="Location",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:map-marker-outline",
        value_fn=data_value("location"),
        exists_fn=has_data("location"),
    ),
    XSenseSensorEntityDescription(
        key="color",
        name="Color",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:palette",
        value_fn=data_value("color"),
        exists_fn=has_data("color"),
    ),
    XSenseSensorEntityDescription(
        key="light_scene",
        name="Light Scene",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:palette-outline",
        value_fn=data_value("lightScene"),
        exists_fn=has_data("lightScene"),
    ),
    XSenseSensorEntityDescription(
        key="light_event",
        name="Light Event",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lightbulb-alert-outline",
        value_fn=data_value("onEvent"),
        exists_fn=has_data("onEvent"),
    ),
    XSenseSensorEntityDescription(
        key="device_type",
        name="Device Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shape-outline",
        value_fn=data_value("devType"),
        exists_fn=has_data("devType"),
    ),
    XSenseSensorEntityDescription(
        key="reported_device_type",
        name="Reported Device Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shape-outline",
        value_fn=data_value("deviceType"),
        exists_fn=has_data("deviceType"),
    ),
    XSenseSensorEntityDescription(
        key="category",
        name="Category",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shape",
        value_fn=data_value("category"),
        exists_fn=has_data("category"),
    ),
    XSenseSensorEntityDescription(
        key="safe_mode",
        name="Safe Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-home",
        value_fn=data_value("safeMode"),
        exists_fn=has_data("safeMode"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the xsense sensor entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator.data["stations"].values():
        devices.extend(
            XSenseSensorEntity(coordinator, station, description)
            for description in SENSORS
            if description.exists_fn(station)
        )
    for dev in coordinator.data["devices"].values():
        devices.extend(
            XSenseSensorEntity(
                coordinator, dev, description, station_id=dev.station.entity_id
            )
            for description in SENSORS
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseSensorEntity(XSenseEntity, SensorEntity):
    """Representation of a xsense device."""

    entity_description: XSenseSensorEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseSensorEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self.entity_description = entity_description
        self._attr_available = False  # This overrides the default

        super().__init__(coordinator, entity, station_id)

    @property
    def native_value(self) -> str | int | float | datetime | None:
        """Return the state of the sensor."""
        device = self._current_entity()
        if device is None:
            return None

        return self.entity_description.value_fn(device)
