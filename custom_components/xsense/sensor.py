"""Support for xsense sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.device import Device
from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType, entities

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

from .const import DOMAIN, NON_ENTITY_DIAGNOSTIC_SENSOR_KEYS, STATE_SIGNAL
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


# These models report physical self-tests but have no remote self-test command.
SELF_TEST_REPORT_ONLY_MODELS = {"SC06-WX", "XS01-WX", "XS0B-iR"}


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


def optional_data_value(key: str) -> Callable[[Entity], StateType]:
    """Return an optional value function for late-reporting X-Sense data."""
    return lambda entity: entity.data.get(key)


def sbs50_station(entity: Entity) -> bool:
    """Return whether this entity is an SBS50 base station."""
    return entity.type == "SBS50"


def co_device(entity: Entity) -> bool:
    """Return whether this entity is a CO-capable detector."""
    entity_def = entities.get(entity.type) or {}
    return entity_def.get("type") in {
        EntityType.CO,
        EntityType.COMBI,
    } or entity.type.startswith("XC")


def has_device_status(entity: Entity) -> bool:
    """Return whether the APK presents a combined current device status."""
    entity_def = entities.get(entity.type) or {}
    return "isLifeEnd" in entity.data or entity_def.get("type") in {
        EntityType.CO,
        EntityType.COMBI,
        EntityType.SMOKE,
    }


def apk_device_status(entity: Entity) -> str:
    """Return the APK current-status value using its exact precedence."""
    if str(entity.data.get("isLifeEnd", "")).strip() == "1":
        return "end_of_life"
    if str(entity.data.get("sensorStatus", "")).strip() == "1":
        return "malfunction"
    try:
        if int(entity.data["batInfo"]) <= 1:
            return "low_battery"
    except (KeyError, TypeError, ValueError):
        pass
    return "normal"


def has_data_or_sbs50(key: str) -> Callable[[Entity], bool]:
    """Create SBS50 base entities even before late shadow keys arrive."""
    return lambda entity: key in entity.data or sbs50_station(entity)


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
    if str(value).strip().lower() in {"0", "success", "successful", "ok", "pass"}:
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
    return (
        entity.type in SELF_TEST_REPORT_ONLY_MODELS
        or "lastSelfTest" in entity.data
        or any(
            action.get("action") == "test"
            for action in entity_def.get("actions", [])
        )
    )


_ALL_SENSORS: tuple[XSenseSensorEntityDescription, ...] = (
    XSenseSensorEntityDescription(
        key="device_status",
        translation_key="device_status",
        device_class=SensorDeviceClass.ENUM,
        options=("normal", "low_battery", "malfunction", "end_of_life"),
        icon="mdi:shield-check-outline",
        exists_fn=has_device_status,
        value_fn=apk_device_status,
    ),
    XSenseSensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=has_data_or_sbs50("wifiRSSI"),
        value_fn=optional_data_value("wifiRSSI"),
    ),
    XSenseSensorEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:access-point-network",
        exists_fn=has_data_or_sbs50("ssid"),
        value_fn=optional_data_value("ssid"),
    ),
    XSenseSensorEntityDescription(
        key="wifi_sw",
        translation_key="wifi_sw",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        exists_fn=lambda device: "wifi_sw" in device.data,
        value_fn=lambda station: station.data["wifi_sw"],
    ),
    XSenseSensorEntityDescription(
        key="ip",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network-outline",
        exists_fn=has_data_or_sbs50("ip"),
        value_fn=optional_data_value("ip"),
    ),
    XSenseSensorEntityDescription(
        key="co",
        translation_key="co_reading",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=optional_data_value("coPpm"),
        exists_fn=lambda device: "coPpm" in device.data or co_device(device),
    ),
    XSenseSensorEntityDescription(
        key="co_peak",
        translation_key="peak_co_level",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("coPpmPeak"),
        exists_fn=has_data("coPpmPeak"),
    ),
    XSenseSensorEntityDescription(
        key="co_level",
        translation_key="co_level",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule-co",
        value_fn=optional_data_value("coLevel"),
        exists_fn=lambda device: "coLevel" in device.data or co_device(device),
    ),
    XSenseSensorEntityDescription(
        key="co_peak_time",
        translation_key="peak_co_level_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-alert-outline",
        value_fn=data_value("coPpmPeakTime"),
        exists_fn=has_data("coPpmPeakTime"),
    ),
    XSenseSensorEntityDescription(
        key="radon_peak",
        translation_key="radon_peak",
        native_unit_of_measurement="Bq/m³",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:radioactive",
        value_fn=optional_data_value("radonPeak"),
        exists_fn=lambda device: device.type == "XR0A-iR"
        or "radonPeak" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="radon_peak_time",
        translation_key="radon_peak_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=optional_data_timestamp("radonPeakTime"),
        exists_fn=lambda device: device.type == "XR0A-iR"
        or "radonPeakTime" in device.data,
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
        name="Battery Level",
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
        options=STATE_SIGNAL,
        value_fn=rf_level,
        exists_fn=lambda device: "rfLevel" in device.data,
    ),
    XSenseSensorEntityDescription(
        key="wifi_rssi_level",
        name="Wi-Fi Signal Strength",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-strength-2",
        value_fn=data_value("wifiRssiLevel"),
        exists_fn=has_data("wifiRssiLevel"),
    ),
    XSenseSensorEntityDescription(
        key="camera_signal_strength",
        name="Wi-Fi Signal Strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_value("signalStrength"),
        exists_fn=has_camera_data("signalStrength"),
    ),
    XSenseSensorEntityDescription(
        key="camera_status_code",
        name="Camera Status Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:camera-metering-center",
        value_fn=data_value("cameraStatusCode"),
        exists_fn=has_camera_data("cameraStatusCode"),
    ),
    XSenseSensorEntityDescription(
        key="camera_firmware_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value_fn=data_value("firmwareVersion"),
        exists_fn=has_camera_data("firmwareVersion"),
    ),
    XSenseSensorEntityDescription(
        key="camera_firmware_status",
        name="Camera Firmware Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:update",
        value_fn=data_value("firmwareStatus"),
        exists_fn=has_camera_data("firmwareStatus"),
    ),
    XSenseSensorEntityDescription(
        key="camera_network_name",
        name="Wi-Fi Name (SSID)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
        value_fn=data_value("networkName"),
        exists_fn=has_camera_data("networkName"),
    ),
    XSenseSensorEntityDescription(
        key="camera_wifi_channel",
        name="Wi-Fi Channel",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-cog",
        value_fn=data_value("wifiChannel"),
        exists_fn=has_camera_data("wifiChannel"),
    ),
    XSenseSensorEntityDescription(
        key="camera_wired_mac_address",
        name="MAC Address",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ethernet",
        value_fn=data_value("wiredMacAddress"),
        exists_fn=has_camera_data("wiredMacAddress"),
    ),
    XSenseSensorEntityDescription(
        key="camera_sd_card_status",
        name="SD Card Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sd",
        value_fn=data_value("sdCardFormatStatus"),
        exists_fn=has_camera_data("sdCardFormatStatus"),
    ),
    XSenseSensorEntityDescription(
        key="camera_sd_card_total",
        name="SD Card Total",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sd",
        value_fn=data_value("sdCardTotal"),
        exists_fn=has_camera_data("sdCardTotal"),
    ),
    XSenseSensorEntityDescription(
        key="camera_sd_card_used",
        name="SD Card Used",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sd",
        value_fn=data_value("sdCardUsed"),
        exists_fn=has_camera_data("sdCardUsed"),
    ),
    XSenseSensorEntityDescription(
        key="camera_activated_time",
        name="Camera Activated Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("activatedTime"),
        exists_fn=has_camera_data("activatedTime"),
    ),
    XSenseSensorEntityDescription(
        key="camera_offline_time",
        name="Camera Offline Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("offlineTime"),
        exists_fn=has_camera_data("offlineTime"),
    ),
    XSenseSensorEntityDescription(
        key="camera_thumbnail_time",
        name="Camera Thumbnail Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("thumbImgTime"),
        exists_fn=has_camera_data("thumbImgTime"),
    ),
    XSenseSensorEntityDescription(
        key="camera_dormancy_wake_time",
        name="Camera Dormancy Wake Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=data_timestamp("deviceDormancyWakeTime"),
        exists_fn=has_camera_data("deviceDormancyWakeTime"),
    ),
    XSenseSensorEntityDescription(
        key="camera_dormancy_message",
        name="Camera Dormancy Message",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sleep",
        value_fn=data_value("deviceDormancyMessage"),
        exists_fn=has_camera_data("deviceDormancyMessage"),
    ),
    XSenseSensorEntityDescription(
        key="camera_time_zone_area",
        name="Device Time Zone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:map-clock-outline",
        value_fn=data_value("timeZoneArea"),
        exists_fn=has_camera_data("timeZoneArea"),
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
        key="check_type",
        name="Check Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:checkbox-marked-circle-outline",
        value_fn=data_value("checkType"),
        exists_fn=has_data("checkType"),
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
        name="Sensor Sensitivity",
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
        name="Temperature Alarm Silence Time",
        icon="mdi:thermometer-off",
        value_fn=data_value("tempMuteTime"),
        exists_fn=has_data("tempMuteTime"),
    ),
    XSenseSensorEntityDescription(
        key="water_mute_time",
        name="Water Leak Alarm Silence Time",
        icon="mdi:water-off",
        value_fn=data_value("waterMuteTime"),
        exists_fn=has_data("waterMuteTime"),
    ),
    XSenseSensorEntityDescription(
        key="short_warning",
        name="Short-Term CO Warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-outline",
        value_fn=data_value("warnShort"),
        exists_fn=has_data("warnShort"),
    ),
    XSenseSensorEntityDescription(
        key="short_warning_co",
        name="Short-Term CO Warning Level",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("warnShortCoPpm"),
        exists_fn=has_data("warnShortCoPpm"),
    ),
    XSenseSensorEntityDescription(
        key="long_warning",
        name="Long-Term CO Warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
        value_fn=data_value("warnLong"),
        exists_fn=has_data("warnLong"),
    ),
    XSenseSensorEntityDescription(
        key="long_warning_co",
        name="Long-Term CO Warning Level",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=data_value("warnLongCoPpm"),
        exists_fn=has_data("warnLongCoPpm"),
    ),
    XSenseSensorEntityDescription(
        key="alarm_occur",
        name="Alarm Occurrence",
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
        name="Repeated Alarm",
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
        key="test_time",
        name="Device Test Time",
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
        key="timezone",
        name="Device Time Zone",
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
        value_fn=optional_data_value("zoneName"),
        exists_fn=has_data_or_sbs50("zoneName"),
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
        name="Security Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-home",
        value_fn=optional_data_value("safeMode"),
        exists_fn=has_data_or_sbs50("safeMode"),
    ),
)

SENSORS = tuple(
    description
    for description in _ALL_SENSORS
    if description.key not in NON_ENTITY_DIAGNOSTIC_SENSOR_KEYS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the xsense sensor entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator_stations(coordinator).values():
        devices.extend(
            XSenseSensorEntity(coordinator, station, description)
            for description in SENSORS
            if description.exists_fn(station)
        )
    for dev in coordinator_devices(coordinator).values():
        devices.extend(
            XSenseSensorEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
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
