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


def has_data(*keys: str) -> Callable[[Entity], bool]:
    """Return an exists function for required X-Sense data keys."""
    return lambda entity: (
        is_camera_entity(entity)
        and all(key in entity.data for key in keys)
        and entity.data.get("isAdmin") is True
    )


def has_supported_data(*keys: str, support_key: str) -> Callable[[Entity], bool]:
    """Return if the app exposes a supported camera setting."""
    return lambda entity: (
        is_camera_entity(entity)
        and all(key in entity.data for key in keys)
        and entity.data.get("isAdmin") is True
        and entity.data.get(support_key) is True
    )


def has_shadow_select(key: str) -> Callable[[Entity], bool]:
    """Return if a non-camera X-Sense shadow exposes a writable select field."""
    return lambda entity: (
        not is_camera_entity(entity)
        and (key in entity.data or _sbs50_default_select(entity, key))
        and _has_shadow_write_route(entity)
    )


def has_radon_server_setting(entity: Entity) -> bool:
    """Return whether the APK exposes XR0A-iR server-backed settings."""
    station = getattr(entity, "station", entity)
    return (
        entity.type == "XR0A-iR"
        and bool(getattr(station, "entity_id", None))
        and bool(getattr(station, "sn", None))
    )


def _sbs50_default_select(entity: Entity, key: str) -> bool:
    """Return whether the APK exposes this SBS50 select before first shadow data."""
    return entity.type == "SBS50" and key in {"alarmTone", "ledBrt"}


def _has_shadow_write_route(entity: Entity) -> bool:
    """Return if an entity has the serial context needed for shadow writes."""
    if not getattr(entity, "sn", None):
        return False
    station = getattr(entity, "station", entity)
    return bool(getattr(station, "sn", None) and getattr(station, "shadow_name", None))


def has_camera_motion_sensitivity(entity: Entity) -> bool:
    """Return if the app exposes camera motion sensitivity controls."""
    return (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and (
            "motionSensitivity" in entity.data
            or "motionSensitivityOptionList" in entity.data
            or "needMotion" in entity.data
        )
    )


def has_camera_video_seconds(entity: Entity) -> bool:
    """Return if the app exposes camera recording duration controls."""
    options = entity.data.get("videoSecondsValues")
    return (
        is_camera_entity(entity)
        and entity.data.get("isAdmin") is True
        and isinstance(options, list)
        and any(option is not None for option in options)
    )


def option_strings(value) -> list[str]:
    """Return API-provided options as strings for Home Assistant selects."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def shadow_select_options(entity: Entity, description) -> list[str]:
    """Return conservative APK option values for non-camera settings."""
    if description.fixed_options is not None:
        return option_strings(list(description.fixed_options))
    value = entity.data.get(description.data_key)
    return [] if value in (None, "") else [str(value)]


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
class XSenseSelectEntityDescription(SelectEntityDescription):
    """Describes X-Sense select entity."""

    data_key: str
    options_key: str | None = None
    exists_fn: Callable[[Entity], bool]
    addx_key: str | None = None
    fixed_options: tuple[int | str, ...] | None = None
    light_on_event: str | None = None
    entity_category: EntityCategory | None = EntityCategory.CONFIG


SELECTS: tuple[XSenseSelectEntityDescription, ...] = (
    XSenseSelectEntityDescription(
        key="alarm_tone",
        data_key="alarmTone",
        translation_key="alarm_tone",
        fixed_options=("1", "2", "3"),
        icon="mdi:bell-ring",
        exists_fn=has_shadow_select("alarmTone"),
    ),
    XSenseSelectEntityDescription(
        key="chirp_tone",
        data_key="chirpTone",
        translation_key="chirp_tone",
        fixed_options=("1", "2", "3"),
        icon="mdi:volume-high",
        exists_fn=has_shadow_select("chirpTone"),
    ),
    XSenseSelectEntityDescription(
        key="reminder_tone",
        data_key="remindTone",
        translation_key="reminder_tone",
        fixed_options=("1", "2", "3"),
        icon="mdi:bell-clock",
        exists_fn=has_shadow_select("remindTone"),
    ),
    XSenseSelectEntityDescription(
        key="alarm_interval",
        data_key="alarmInterval",
        translation_key="alarm_interval",
        fixed_options=("50", "60", "90", "120", "180"),
        icon="mdi:timer-outline",
        exists_fn=has_shadow_select("alarmInterval"),
    ),
    XSenseSelectEntityDescription(
        key="reminder_time",
        data_key="remindTime",
        translation_key="reminder_time",
        fixed_options=("9:00", "12:00", "15:00", "18:00"),
        icon="mdi:bell-clock",
        exists_fn=has_shadow_select("remindTime"),
    ),
    XSenseSelectEntityDescription(
        key="mailbox_report_interval",
        data_key="reportInterval",
        translation_key="mailbox_report_interval",
        fixed_options=(
            "2",
            "5",
            "10",
            "15",
            "30",
            "60",
            "120",
            "240",
            "360",
            "480",
            "720",
        ),
        icon="mdi:mailbox-clock-outline",
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.MAILBOX
            and has_shadow_select("reportInterval")(entity)
        ),
    ),
    XSenseSelectEntityDescription(
        key="temperature_unit",
        data_key="tempUnit",
        translation_key="temperature_unit",
        fixed_options=("1", "2"),
        icon="mdi:temperature-celsius",
        exists_fn=has_shadow_select("tempUnit"),
    ),
    XSenseSelectEntityDescription(
        key="radon_unit",
        data_key="radonUnit",
        translation_key="radon_unit",
        fixed_options=("1", "2"),
        icon="mdi:radioactive",
        exists_fn=has_radon_server_setting,
    ),
    XSenseSelectEntityDescription(
        key="comfort_type",
        data_key="comfortType",
        translation_key="comfort_type",
        fixed_options=("0", "1"),
        icon="mdi:home-thermometer-outline",
        exists_fn=has_shadow_select("comfortType"),
    ),
    XSenseSelectEntityDescription(
        key="led_brightness",
        data_key="ledBrt",
        translation_key="led_brightness",
        fixed_options=("2", "4", "6", "8"),
        icon="mdi:led-on",
        exists_fn=has_shadow_select("ledBrt"),
    ),
    XSenseSelectEntityDescription(
        key="light_motion_on_time",
        data_key="pirTime",
        translation_key="light_motion_on_time",
        fixed_options=("30", "60", "180", "300", "600", "900"),
        icon="mdi:timer-outline",
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.LIGHT
            and has_shadow_select("pirTime")(entity)
        ),
        light_on_event="1",
    ),
    XSenseSelectEntityDescription(
        key="light_scene",
        data_key="lightScene",
        translation_key="light_scene",
        fixed_options=("1", "2", "3"),
        icon="mdi:lightbulb-group",
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.LIGHT
            and has_shadow_select("lightScene")(entity)
        ),
    ),
    XSenseSelectEntityDescription(
        key="light_app_on_time",
        data_key="appTime",
        translation_key="light_app_on_time",
        fixed_options=("30", "60", "180", "300", "600", "900"),
        icon="mdi:timer-outline",
        exists_fn=lambda entity: (
            getattr(entity, "entity_type", None) == EntityType.LIGHT
            and has_shadow_select("appTime")(entity)
        ),
        light_on_event="2",
    ),
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
        fixed_options=(0, 1, 2, 3),
        name="Detection Sensitivity",
        icon="mdi:motion-sensor",
        exists_fn=has_camera_motion_sensitivity,
    ),
    XSenseSelectEntityDescription(
        key="camera_video_seconds",
        data_key="videoSeconds",
        addx_key="videoSeconds",
        options_key="videoSecondsValues",
        name="Video Duration",
        icon="mdi:timer-outline",
        exists_fn=has_camera_video_seconds,
    ),
    XSenseSelectEntityDescription(
        key="camera_antiflicker_rate",
        data_key="antiflicker",
        addx_key="antiflicker",
        fixed_options=(50, 60),
        name="Flicker Frequency",
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
            is_camera_entity(entity)
            and "defaultCodec" in entity.data
            and entity.data.get("isAdmin") is True
            and entity.data.get("showCodecChange") is True
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_motion_tracking_mode",
        data_key="motionTrackMode",
        addx_key="motionTrackMode",
        fixed_options=(0, 1),
        name="Motion Tracking",
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
        name="Cloud Cool Down Time",
        icon="mdi:timer-sand",
        exists_fn=lambda entity: (
            is_camera_entity(entity)
            and "cooldownValue" in entity.data
            and entity.data.get("isAdmin") is True
            and "cooldownOptions" in entity.data
            and entity.data.get("cooldownSupported") is True
            and entity.data.get("supportPirCooldown") is True
        ),
    ),
    XSenseSelectEntityDescription(
        key="camera_doorbell_ring_key",
        data_key="doorBellRingKey",
        addx_key="audio.doorBellRingKey",
        options_key="doorBellRingKeyOptions",
        name="Doorbell Tone",
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
    seen_entity_ids: set[str] = set()

    for station in coordinator_stations(coordinator).values():
        seen_entity_ids.add(station.entity_id)
        devices.extend(
            XSenseSelectEntity(coordinator, station, description)
            for description in SELECTS
            if description.exists_fn(station)
        )

    for dev in coordinator_devices(coordinator).values():
        if dev.entity_id in seen_entity_ids:
            continue
        devices.extend(
            XSenseSelectEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in SELECTS
            if description.exists_fn(dev)
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
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self.entity_description = entity_description
        self._attr_available = False
        super().__init__(coordinator, entity, station_id)

    @property
    def available(self) -> bool:
        """Return if this control can be used."""
        return self._current_entity_is_online()

    @property
    def options(self) -> list[str]:
        """Return the API-provided valid options."""
        entity = self._current_entity()
        if entity is None:
            return []
        if self.entity_description.key == "camera_motion_sensitivity":
            options = entity.data.get("motionSensitivityOptionList")
            if isinstance(options, list) and len(options) == 4:
                return option_strings(options)
        if not is_camera_entity(entity):
            return shadow_select_options(entity, self.entity_description)
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
                user_enable=_required_bool_state(entity.data.get("cooldownEnabled")),
                value=int(_typed_option(option)),
            )
        elif self.entity_description.addx_key and self.entity_description.addx_key.startswith(
            "audio."
        ):
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
        elif not is_camera_entity(entity):
            if self.entity_description.data_key == "radonUnit":
                await self.coordinator.xsense.update_radon_unit(entity, option)
            elif self.entity_description.data_key == "comfortType":
                await self._async_select_comfort_type(entity, option)
            elif self.entity_description.data_key == "lightScene":
                await self.coordinator.xsense.update_light_scene(entity, option)
                entity.data["pirEnable"] = option in {"1", "3"}
                entity.data["awaitEnable"] = option in {"2", "3"}
            elif self.entity_description.light_on_event is not None:
                await self.coordinator.xsense.update_light_setting(
                    entity,
                    self.entity_description.data_key,
                    option,
                    on_event=self.entity_description.light_on_event,
                )
            else:
                await self.coordinator.xsense.update_shadow_setting(
                    entity, self.entity_description.data_key, option
                )
        else:
            raise HomeAssistantError("X-Sense select cannot be written")

        entity.data[self.entity_description.data_key] = _typed_option(option)
        self.coordinator.async_update_listeners()

    async def _async_select_comfort_type(self, entity: Entity, option: str) -> None:
        """Write comfort mode with the same paired defaults the APK sends."""
        if option == "0":
            await self.coordinator.xsense.update_shadow_settings(
                entity,
                {"tComfort": [20.0, 26.0], "hComfort": [30.0, 60.0]},
                comfort_type="0",
            )
            entity.data["tComfort"] = [20.0, 26.0]
            entity.data["hComfort"] = [30.0, 60.0]
            return

        t_comfort = _comfort_pair(entity.data.get("tComfort"), [20.0, 26.0])
        h_comfort = _comfort_pair(entity.data.get("hComfort"), [30.0, 60.0])
        await self.coordinator.xsense.update_shadow_settings(
            entity,
            {"tComfort": t_comfort, "hComfort": h_comfort},
            comfort_type="1",
        )
        entity.data["tComfort"] = t_comfort
        entity.data["hComfort"] = h_comfort


def _typed_option(option: str) -> int | str:
    """Return option as int when the API supplied numeric options."""
    try:
        return int(option)
    except ValueError:
        return option


def _comfort_pair(value, default: list[float]) -> list[float]:
    """Return a comfort range pair for APK comfort mode writes."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return [float(value[0]), float(value[1])]
        except (TypeError, ValueError):
            pass
    return list(default)
