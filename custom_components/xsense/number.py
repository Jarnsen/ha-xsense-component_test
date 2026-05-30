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

from .api.async_xsense import CAMERA_TYPES
from .api.device import Device
from .api.entity import Entity
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for a X-Sense data key."""
    return lambda entity: key in entity.data and entity.data.get("isAdmin", True)


def has_supported_data(key: str, support_key: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a supported camera setting."""
    return lambda entity: (
        key in entity.data
        and entity.data.get("isAdmin", True)
        and entity.data.get(support_key, True)
    )


@dataclass(kw_only=True, frozen=True)
class XSenseNumberEntityDescription(NumberEntityDescription):
    """Describes X-Sense number entity."""

    data_key: str
    addx_key: str
    exists_fn: Callable[[Entity], bool]
    entity_category: EntityCategory | None = EntityCategory.CONFIG


NUMBERS: tuple[XSenseNumberEntityDescription, ...] = (
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
        exists_fn=has_supported_data("liveSpeakerVolume", "supportLiveSpeakerVolume"),
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
            "cooldownValue" in entity.data
            and entity.data.get("isAdmin", True)
            and "cooldownOptions" not in entity.data
            and entity.data.get("cooldownSupported", True)
            and entity.data.get("supportPirCooldown", True)
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
            if station.type in CAMERA_TYPES and description.exists_fn(station)
        )

    async_add_entities(devices)


class XSenseNumberEntity(XSenseEntity, NumberEntity):
    """Numeric settings for X-Sense cameras."""

    entity_description: XSenseNumberEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseNumberEntityDescription,
    ) -> None:
        """Set up the instance."""
        self.entity_description = entity_description
        self._attr_available = False
        super().__init__(coordinator, entity)

    @property
    def native_value(self) -> float | None:
        """Return the number value."""
        entity = self._current_entity()
        if entity is None:
            return None
        value = entity.data.get(self.entity_description.data_key)
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write the camera setting through the ADDX user-config endpoint."""
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        int_value = round(value)
        if self.entity_description.addx_key == "cooldown.value":
            await self.coordinator.xsense.update_camera_cooldown(
                entity,
                user_enable=bool(entity.data.get("cooldownEnabled")),
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
