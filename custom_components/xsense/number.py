"""Support for X-Sense numeric settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant import config_entries
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.device import Device
from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for a X-Sense data key."""
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


def has_shadow_volume(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera X-Sense shadow exposes a writable volume field."""

    def exists(entity: Entity) -> bool:
        if (
            is_camera_entity(entity)
            or key not in entity.data
            or not _has_shadow_write_route(entity)
        ):
            return False
        return True

    return exists


def has_shadow_number(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera X-Sense shadow exposes a writable numeric field."""
    return lambda entity: (
        not is_camera_entity(entity)
        and key in entity.data
        and _has_shadow_write_route(entity)
    )


def _has_shadow_write_route(entity: Entity) -> bool:
    """Return if an entity has the serial context needed for shadow writes."""
    if not getattr(entity, "sn", None):
        return False
    station = getattr(entity, "station", entity)
    return bool(getattr(station, "sn", None) and getattr(station, "shadow_name", None))


def _required_bool_state(value) -> bool:
    """Return an explicit X-Sense boolean value or raise if it is unknown."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on"}:
            return True
        if normalized in {"0", "false", "off"}:
            return False
    raise HomeAssistantError("X-Sense cooldown enabled state is unknown")


@dataclass(kw_only=True, frozen=True)
class XSenseNumberEntityDescription(NumberEntityDescription):
    """Describes X-Sense number entity."""

    data_key: str
    exists_fn: Callable[[Entity], bool]
    addx_key: str | None = None
    shadow_array_key: str | None = None
    shadow_array_index: int | None = None
    shadow_array_defaults: tuple[float, float] | None = None
    shadow_array_comfort_type: str | None = None
    shadow_setting: bool = False
    light_on_event: str | None = None
    entity_category: EntityCategory | None = EntityCategory.CONFIG


NUMBERS: tuple[XSenseNumberEntityDescription, ...] = (
    XSenseNumberEntityDescription(
        key="alarm_volume",
        data_key="alarmVol",
        translation_key="alarm_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("alarmVol"),
    ),
    XSenseNumberEntityDescription(
        key="voice_volume",
        data_key="voiceVol",
        translation_key="voice_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("voiceVol"),
    ),
    XSenseNumberEntityDescription(
        key="chirp_volume",
        data_key="chirpVol",
        translation_key="chirp_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("chirpVol"),
    ),
    XSenseNumberEntityDescription(
        key="reminder_volume",
        data_key="remindVol",
        translation_key="reminder_volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_shadow_volume("remindVol"),
    ),
    XSenseNumberEntityDescription(
        key="temperature_adjustment",
        data_key="tAdjust",
        translation_key="temperature_adjustment",
        icon="mdi:thermometer-lines",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-10,
        native_max_value=10,
        native_step=0.1,
        exists_fn=has_shadow_number("tAdjust"),
        shadow_setting=True,
    ),
    XSenseNumberEntityDescription(
        key="humidity_adjustment",
        data_key="hAdjust",
        translation_key="humidity_adjustment",
        icon="mdi:water-percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        exists_fn=has_shadow_number("hAdjust"),
        shadow_setting=True,
    ),
    XSenseNumberEntityDescription(
        key="detection_sensitivity",
        data_key="detcSens",
        translation_key="detection_sensitivity",
        icon="mdi:smoke-detector-variant",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
        exists_fn=has_shadow_number("detcSens"),
        shadow_setting=True,
    ),
    XSenseNumberEntityDescription(
        key="driveway_sensitivity",
        data_key="sensitivity",
        translation_key="driveway_sensitivity",
        icon="mdi:motion-sensor",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
        exists_fn=has_shadow_number("sensitivity"),
        shadow_setting=True,
    ),
    XSenseNumberEntityDescription(
        key="trigger_brightness",
        data_key="triggerBrightness",
        translation_key="trigger_brightness",
        icon="mdi:brightness-6",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.LIGHT
            and has_shadow_number("triggerBrightness")(entity)
        ),
        light_on_event="0",
    ),
    XSenseNumberEntityDescription(
        key="standby_brightness",
        data_key="awaitBrightness",
        translation_key="standby_brightness",
        icon="mdi:brightness-5",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.LIGHT
            and has_shadow_number("awaitBrightness")(entity)
        ),
        light_on_event="0",
    ),
    XSenseNumberEntityDescription(
        key="warning_period",
        data_key="warnPeriod",
        translation_key="warning_period",
        icon="mdi:calendar-clock",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        exists_fn=has_shadow_number("warnPeriod"),
    ),
    XSenseNumberEntityDescription(
        key="temperature_min",
        data_key="tempRangeMin",
        translation_key="temperature_min",
        icon="mdi:thermometer-low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40,
        native_max_value=60,
        native_step=0.1,
        shadow_array_key="tRange",
        shadow_array_index=0,
        exists_fn=lambda entity: _has_shadow_range_number(
            entity, "tRange", "tempRangeMin", "tempRangeMax"
        ),
    ),
    XSenseNumberEntityDescription(
        key="temperature_max",
        data_key="tempRangeMax",
        translation_key="temperature_max",
        icon="mdi:thermometer-high",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40,
        native_max_value=60,
        native_step=0.1,
        shadow_array_key="tRange",
        shadow_array_index=1,
        exists_fn=lambda entity: _has_shadow_range_number(
            entity, "tRange", "tempRangeMin", "tempRangeMax"
        ),
    ),
    XSenseNumberEntityDescription(
        key="humidity_min",
        data_key="humRangeMin",
        translation_key="humidity_min",
        icon="mdi:water-percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        shadow_array_key="hRange",
        shadow_array_index=0,
        exists_fn=lambda entity: _has_shadow_range_number(
            entity, "hRange", "humRangeMin", "humRangeMax"
        ),
    ),
    XSenseNumberEntityDescription(
        key="humidity_max",
        data_key="humRangeMax",
        translation_key="humidity_max",
        icon="mdi:water-percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        shadow_array_key="hRange",
        shadow_array_index=1,
        exists_fn=lambda entity: _has_shadow_range_number(
            entity, "hRange", "humRangeMin", "humRangeMax"
        ),
    ),
    XSenseNumberEntityDescription(
        key="temperature_comfort_min",
        data_key="tComfortMin",
        translation_key="temperature_comfort_min",
        icon="mdi:home-thermometer-outline",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40,
        native_max_value=60,
        native_step=0.1,
        shadow_array_key="tComfort",
        shadow_array_index=0,
        shadow_array_defaults=(20, 26),
        shadow_array_comfort_type="1",
        exists_fn=lambda entity: _has_shadow_range_number(entity, "tComfort"),
    ),
    XSenseNumberEntityDescription(
        key="temperature_comfort_max",
        data_key="tComfortMax",
        translation_key="temperature_comfort_max",
        icon="mdi:home-thermometer-outline",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-40,
        native_max_value=60,
        native_step=0.1,
        shadow_array_key="tComfort",
        shadow_array_index=1,
        shadow_array_defaults=(20, 26),
        shadow_array_comfort_type="1",
        exists_fn=lambda entity: _has_shadow_range_number(entity, "tComfort"),
    ),
    XSenseNumberEntityDescription(
        key="humidity_comfort_min",
        data_key="hComfortMin",
        translation_key="humidity_comfort_min",
        icon="mdi:home-thermometer-outline",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        shadow_array_key="hComfort",
        shadow_array_index=0,
        shadow_array_defaults=(30, 60),
        shadow_array_comfort_type="1",
        exists_fn=lambda entity: _has_shadow_range_number(entity, "hComfort"),
    ),
    XSenseNumberEntityDescription(
        key="humidity_comfort_max",
        data_key="hComfortMax",
        translation_key="humidity_comfort_max",
        icon="mdi:home-thermometer-outline",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        shadow_array_key="hComfort",
        shadow_array_index=1,
        shadow_array_defaults=(30, 60),
        shadow_array_comfort_type="1",
        exists_fn=lambda entity: _has_shadow_range_number(entity, "hComfort"),
    ),
    XSenseNumberEntityDescription(
        key="camera_alarm_volume",
        data_key="alarmVol",
        addx_key="alarmVolume",
        name="Alarm Volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_supported_data("alarmVol", "supportAlarmVolume"),
    ),
    XSenseNumberEntityDescription(
        key="camera_voice_volume",
        data_key="voiceVol",
        addx_key="voiceVolume",
        name="Voice Volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_supported_data("voiceVol", "supportVoiceVolume"),
    ),
    XSenseNumberEntityDescription(
        key="camera_live_speaker_volume",
        data_key="liveSpeakerVolume",
        addx_key="audio.liveSpeakerVolume",
        name="Live Speaker Volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        exists_fn=has_apk_default_supported_data(
            "liveSpeakerVolume", "supportLiveSpeakerVolume"
        ),
    ),
    XSenseNumberEntityDescription(
        key="camera_alarm_seconds",
        data_key="alarmSeconds",
        addx_key="alarmSeconds",
        name="Alarm Seconds",
        icon="mdi:timer-outline",
        native_min_value=0,
        native_max_value=300,
        native_step=1,
        exists_fn=has_supported_data("alarmSeconds", "supportAlarm"),
    ),
    XSenseNumberEntityDescription(
        key="camera_night_threshold",
        data_key="nightThresholdLevel",
        addx_key="nightThresholdLevel",
        name="Night Threshold",
        icon="mdi:weather-night",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
        exists_fn=has_data("nightThresholdLevel"),
    ),
    XSenseNumberEntityDescription(
        key="camera_cry_detection_level",
        data_key="cryDetectLevel",
        addx_key="cryDetectLevel",
        name="Cry Detection Level",
        icon="mdi:baby-face-outline",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
        exists_fn=has_supported_data("cryDetectLevel", "supportCryDetect"),
    ),
    XSenseNumberEntityDescription(
        key="camera_cooldown",
        data_key="cooldownValue",
        addx_key="cooldown.value",
        name="Cooldown",
        icon="mdi:timer-sand",
        native_min_value=5,
        native_max_value=300,
        native_step=1,
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and "cooldownValue" in entity.data
            and entity.data.get("isAdmin") is True
            and "cooldownOptions" not in entity.data
            and entity.data.get("cooldownSupported") is True
            and entity.data.get("supportPirCooldown") is True
        ),
    ),
    XSenseNumberEntityDescription(
        key="camera_mechanical_ding_dong_duration",
        data_key="mechanicalDingDongDuration",
        addx_key="mechanicalDingDongDuration",
        name="Mechanical Ding-Dong Duration",
        icon="mdi:bell-ring",
        native_min_value=0,
        native_max_value=30,
        native_step=1,
        exists_fn=has_supported_data(
            "mechanicalDingDongDuration", "supportMechanicalDingDong"
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense number entities."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    seen_entity_ids: set[str] = set()

    for station in coordinator_stations(coordinator).values():
        seen_entity_ids.add(station.entity_id)
        devices.extend(
            XSenseNumberEntity(coordinator, station, description)
            for description in NUMBERS
            if description.exists_fn(station)
        )

    for dev in coordinator_devices(coordinator).values():
        if dev.entity_id in seen_entity_ids:
            continue
        devices.extend(
            XSenseNumberEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in NUMBERS
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseNumberEntity(XSenseEntity, NumberEntity):
    """Numeric settings for X-Sense devices."""

    entity_description: XSenseNumberEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseNumberEntityDescription,
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
    def native_value(self) -> float | None:
        """Return the number value."""
        entity = self._current_entity()
        if entity is None:
            return None
        value = entity.data.get(self.entity_description.data_key)
        if self.entity_description.shadow_array_key:
            value = _shadow_array_value(entity, self.entity_description)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the X-Sense numeric setting."""
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        if self.entity_description.data_key == "warnPeriod":
            int_value = round(value)
            await self.coordinator.xsense.update_co_pre_alarm(entity, period=int_value)
            entity.data[self.entity_description.data_key] = int_value
        elif self.entity_description.shadow_array_key:
            values = _updated_shadow_array_values(
                entity, self.entity_description, value
            )
            await self.coordinator.xsense.update_shadow_array_setting(
                entity,
                self.entity_description.shadow_array_key,
                values,
                comfort_type=self.entity_description.shadow_array_comfort_type,
            )
            _store_shadow_array_values(entity, self.entity_description, values)
        elif self.entity_description.light_on_event is not None:
            int_value = round(value)
            await self.coordinator.xsense.update_light_setting(
                entity,
                self.entity_description.data_key,
                int_value,
                on_event=self.entity_description.light_on_event,
            )
            entity.data[self.entity_description.data_key] = int_value
        elif self.entity_description.shadow_setting:
            await self.coordinator.xsense.update_shadow_setting(
                entity, self.entity_description.data_key, value
            )
            entity.data[self.entity_description.data_key] = value
        elif self.entity_description.addx_key is None:
            int_value = round(value)
            await self.coordinator.xsense.update_shadow_volume(
                entity, self.entity_description.data_key, int_value
            )
            entity.data[self.entity_description.data_key] = int_value
        elif self.entity_description.addx_key == "cooldown.value":
            int_value = round(value)
            await self.coordinator.xsense.update_camera_cooldown(
                entity,
                user_enable=_required_bool_state(entity.data.get("cooldownEnabled")),
                value=int_value,
            )
            entity.data[self.entity_description.data_key] = int_value
        elif self.entity_description.addx_key.startswith("audio."):
            int_value = round(value)
            await self.coordinator.xsense.update_camera_audio(
                entity,
                **{self.entity_description.addx_key.removeprefix("audio."): int_value},
            )
            entity.data[self.entity_description.data_key] = int_value
        else:
            int_value = round(value)
            await self.coordinator.xsense.update_camera_config(
                entity, **{self.entity_description.addx_key: int_value}
            )
            entity.data[self.entity_description.data_key] = int_value
        self.coordinator.async_update_listeners()


def _has_shadow_range_number(
    entity: Entity,
    array_key: str,
    min_key: str | None = None,
    max_key: str | None = None,
) -> bool:
    """Return if the app exposes a paired range setting for this entity."""
    if is_camera_entity(entity) or not _has_shadow_write_route(entity):
        return False
    if _number_pair(entity.data.get(array_key)) is not None:
        return True
    if array_key in {"tComfort", "hComfort"} and "comfortType" in entity.data:
        return True
    return bool(
        min_key
        and max_key
        and entity.data.get(min_key) is not None
        and entity.data.get(max_key) is not None
    )


def _number_pair(value) -> list[float] | None:
    """Return a two-number list from an APK range payload."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return [float(value[0]), float(value[1])]
    except (TypeError, ValueError):
        return None


def _shadow_array_values(entity: Entity, description) -> list[float] | None:
    """Return current paired values for a range-backed setting."""
    values = _number_pair(entity.data.get(description.shadow_array_key))
    if values is not None:
        return values
    if description.data_key == "tempRangeMin" or description.data_key == "tempRangeMax":
        if (
            entity.data.get("tempRangeMin") is not None
            and entity.data.get("tempRangeMax") is not None
        ):
            return [float(entity.data["tempRangeMin"]), float(entity.data["tempRangeMax"])]
    if description.data_key == "humRangeMin" or description.data_key == "humRangeMax":
        if (
            entity.data.get("humRangeMin") is not None
            and entity.data.get("humRangeMax") is not None
        ):
            return [float(entity.data["humRangeMin"]), float(entity.data["humRangeMax"])]
    if description.shadow_array_defaults is not None:
        return list(description.shadow_array_defaults)
    return None


def _shadow_array_value(entity: Entity, description) -> float | None:
    """Return the current value for one side of a range-backed setting."""
    values = _shadow_array_values(entity, description)
    if values is None or description.shadow_array_index is None:
        return None
    return values[description.shadow_array_index]


def _updated_shadow_array_values(
    entity: Entity, description, value: float
) -> list[float]:
    """Return a paired APK range payload with one side updated."""
    values = _shadow_array_values(entity, description)
    if values is None or description.shadow_array_index is None:
        raise HomeAssistantError("X-Sense range setting is missing its paired value")
    values[description.shadow_array_index] = float(value)
    if values[0] > values[1]:
        raise HomeAssistantError("X-Sense minimum cannot be greater than maximum")
    return values


def _store_shadow_array_values(entity: Entity, description, values: list[float]) -> None:
    """Update cached values after a successful range-backed write."""
    entity.data[description.shadow_array_key] = values
    if description.shadow_array_key == "tRange":
        entity.data["tempRangeMin"], entity.data["tempRangeMax"] = values
    elif description.shadow_array_key == "hRange":
        entity.data["humRangeMin"], entity.data["humRangeMax"] = values
