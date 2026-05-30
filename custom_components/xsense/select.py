"""Support for X-Sense select settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant import config_entries
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.async_xsense import CAMERA_TYPES
from .api.device import Device
from .api.entity import Entity
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


def has_data(*keys: str) -> Callable[[Entity], bool]:
    """Return an exists function for required X-Sense data keys."""
    return lambda entity: (
        all(key in entity.data for key in keys) and entity.data.get("isAdmin", True)
    )


def has_supported_data(*keys: str, support_key: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a supported camera setting."""
    return lambda entity: (
        all(key in entity.data for key in keys)
        and entity.data.get("isAdmin", True)
        and entity.data.get(support_key, True)
    )


def option_strings(value) -> list[str]:
    """Return API-provided options as strings for Home Assistant selects."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


@dataclass(kw_only=True, frozen=True)
class XSenseSelectEntityDescription(SelectEntityDescription):
    """Describes X-Sense select entity."""

    data_key: str
    options_key: str | None = None
    exists_fn: Callable[[Entity], bool]
    addx_key: str | None = None
    fixed_options: tuple[int | str, ...] | None = None
    entity_category: EntityCategory | None = EntityCategory.CONFIG


SELECTS: tuple[XSenseSelectEntityDescription, ...] = (
    XSenseSelectEntityDescription(
        key="camera_language",
        data_key="deviceLanguage",
        addx_key="deviceLanguage",
        options_key="deviceSupportLanguage",
        name="Language",
        icon="mdi:translate",
        exists_fn=has_data("deviceLanguage", "deviceSupportLanguage"),
    ),
    XSenseSelectEntityDescription(
        key="camera_recording_resolution",
        data_key="recResolution",
        options_key="supportedRecordingResolutions",
        name="Recording Resolution",
        icon="mdi:video",
        exists_fn=has_data("recResolution", "supportedRecordingResolutions"),
    ),
    XSenseSelectEntityDescription(
        key="camera_motion_sensitivity",
        data_key="motionSensitivity",
        addx_key="motionSensitivity",
        options_key="motionSensitivityOptionList",
        name="Motion Sensitivity",
        icon="mdi:motion-sensor",
        exists_fn=has_data("motionSensitivity", "motionSensitivityOptionList"),
    ),
    XSenseSelectEntityDescription(
        key="camera_video_seconds",
        data_key="videoSeconds",
        addx_key="videoSeconds",
        options_key="videoSecondsValues",
        name="Video Seconds",
        icon="mdi:timer-outline",
        exists_fn=has_data("videoSeconds", "videoSecondsValues"),
    ),
    XSenseSelectEntityDescription(
        key="camera_antiflicker_rate",
        data_key="antiflicker",
        addx_key="antiflicker",
        fixed_options=(50, 60),
        name="Anti-Flicker Rate",
        icon="mdi:lightbulb-on-10",
        exists_fn=has_supported_data("antiflicker", support_key="supportAntiFlicker"),
    ),
    XSenseSelectEntityDescription(
        key="camera_default_codec",
        data_key="defaultCodec",
        addx_key="defaultCodec",
        fixed_options=("h264", "h265"),
        name="Default Codec",
        icon="mdi:video-settings",
        exists_fn=lambda entity: (
            "defaultCodec" in entity.data
            and entity.data.get("isAdmin", True)
            and entity.data.get("showCodecChange", False)
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_motion_tracking_mode",
        data_key="motionTrackMode",
        addx_key="motionTrackMode",
        fixed_options=(0, 1),
        name="Motion Tracking Mode",
        icon="mdi:axis-arrow",
        exists_fn=has_supported_data(
            "motionTrackMode", support_key="supportMotionTrack"
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_night_vision_mode",
        data_key="nightVisionMode",
        addx_key="nightVisionMode",
        fixed_options=(0, 1),
        name="Night Vision Mode",
        icon="mdi:weather-night",
        exists_fn=has_data("nightVisionMode"),
    ),
    XSenseSelectEntityDescription(
        key="camera_cooldown",
        data_key="cooldownValue",
        addx_key="cooldown.value",
        options_key="cooldownOptions",
        name="Cooldown",
        icon="mdi:timer-sand",
        exists_fn=lambda entity: (
            "cooldownValue" in entity.data
            and entity.data.get("isAdmin", True)
            and "cooldownOptions" in entity.data
            and entity.data.get("cooldownSupported", True)
            and entity.data.get("supportPirCooldown", True)
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_doorbell_ring_key",
        data_key="doorBellRingKey",
        addx_key="audio.doorBellRingKey",
        options_key="doorBellRingKeyOptions",
        name="Doorbell Ring Key",
        icon="mdi:bell-music",
        exists_fn=has_supported_data(
            "doorBellRingKey",
            "doorBellRingKeyOptions",
            support_key="supportMechanicalDingDong",
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_auto_power_on_capacity",
        data_key="chargeAutoPowerOnCapacity",
        addx_key="chargeAutoPowerOnCapacity",
        options_key="chargeAutoPowerOnCapacityOptions",
        name="Auto Power-On Capacity",
        icon="mdi:battery-sync",
        exists_fn=has_supported_data(
            "chargeAutoPowerOnCapacity",
            "chargeAutoPowerOnCapacityOptions",
            support_key="supportChargeAutoPowerOn",
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense select entities."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator.data["stations"].values():
        devices.extend(
            XSenseSelectEntity(coordinator, station, description)
            for description in SELECTS
            if station.type in CAMERA_TYPES and description.exists_fn(station)
        )

    async_add_entities(devices)


class XSenseSelectEntity(XSenseEntity, SelectEntity):
    """Select settings for X-Sense cameras."""

    entity_description: XSenseSelectEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseSelectEntityDescription,
    ) -> None:
        """Set up the instance."""
        self.entity_description = entity_description
        self._attr_available = False
        super().__init__(coordinator, entity)

    @property
    def options(self) -> list[str]:
        """Return the API-provided valid options."""
        entity = self._current_entity()
        if entity is None:
            return []
        if self.entity_description.fixed_options is not None:
            return option_strings(list(self.entity_description.fixed_options))
        return option_strings(entity.data.get(self.entity_description.options_key))

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        entity = self._current_entity()
        if entity is None:
            return None
        value = entity.data.get(self.entity_description.data_key)
        return None if value is None else str(value)

    async def async_select_option(self, option: str) -> None:
        """Write the selected camera setting through the Android app endpoint."""
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")
        if option not in self.options:
            raise HomeAssistantError(f"{option} is not a supported X-Sense option")

        if self.entity_description.data_key == "recResolution":
            await self.coordinator.xsense.update_camera_recording_resolution(
                entity, option
            )
        elif self.entity_description.addx_key == "defaultCodec":
            await self.coordinator.xsense.update_camera_default_codec(entity, option)
        elif self.entity_description.addx_key == "cooldown.value":
            await self.coordinator.xsense.update_camera_cooldown(
                entity,
                user_enable=bool(entity.data.get("cooldownEnabled")),
                value=int(_typed_option(option)),
            )
        elif self.entity_description.addx_key.startswith("audio."):
            await self.coordinator.xsense.update_camera_audio(
                entity,
                **{
                    self.entity_description.addx_key.removeprefix(
                        "audio."
                    ): _typed_option(option)
                },
            )
        elif self.entity_description.addx_key:
            await self.coordinator.xsense.update_camera_config(
                entity, **{self.entity_description.addx_key: _typed_option(option)}
            )
        else:
            raise HomeAssistantError("X-Sense select cannot be written")

        entity.data[self.entity_description.data_key] = _typed_option(option)
        self.coordinator.async_update_listeners()


def _typed_option(option: str) -> int | str:
    """Return option as int when the API supplied numeric options."""
    try:
        return int(option)
    except ValueError:
        return option
