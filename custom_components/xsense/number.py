"""Support for X-Sense numeric settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant import config_entries
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.async_xsense import is_camera_entity
from .api.device import Device
from .api.entity import Entity
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


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


def has_supported_or_unspecified_data(
    key: str, support_key: str
) -> Callable[[Entity], bool]:
    """Return if the APK exposes camera audio when support is unset or enabled."""
    return lambda entity: (
        is_camera_entity(entity)
        and key in entity.data
        and entity.data.get("isAdmin") is True
        and entity.data.get(support_key) is not False
    )


def has_shadow_volume(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera X-Sense shadow exposes a writable volume field."""
    return lambda entity: not is_camera_entity(entity) and key in entity.data


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
        exists_fn=has_supported_or_unspecified_data(
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

    for station in coordinator.data["stations"].values():
        devices.extend(
            XSenseNumberEntity(coordinator, station, description)
            for description in NUMBERS
            if description.exists_fn(station)
        )

    for dev in coordinator.data["devices"].values():
        devices.extend(
            XSenseNumberEntity(
                coordinator, dev, description, station_id=dev.station.entity_id
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

        int_value = round(value)
        if self.entity_description.addx_key is None:
            await self.coordinator.xsense.update_shadow_volume(
                entity, self.entity_description.data_key, int_value
            )
        elif self.entity_description.addx_key == "cooldown.value":
            await self.coordinator.xsense.update_camera_cooldown(
                entity,
                user_enable=_required_bool_state(entity.data.get("cooldownEnabled")),
                value=int_value,
            )
        elif self.entity_description.addx_key.startswith("audio."):
            await self.coordinator.xsense.update_camera_audio(
                entity,
                **{self.entity_description.addx_key.removeprefix("audio."): int_value},
            )
        else:
            await self.coordinator.xsense.update_camera_config(
                entity, **{self.entity_description.addx_key: int_value}
            )
        entity.data[self.entity_description.data_key] = int_value
        self.coordinator.async_update_listeners()
