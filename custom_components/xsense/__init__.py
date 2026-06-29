"""The X-Sense Home Security integration."""

from __future__ import annotations

from contextlib import suppress

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    CONNECTION_NETWORK_MAC,
)
from homeassistant.util import slugify

from .api.async_xsense import is_camera_entity
from .const import (
    CAMERA_AI_SERVICE_AVAILABLE,
    DOMAIN,
)
from .coordinator import XSenseDataUpdateCoordinator
from .media_source import (
    async_register_recording_services,
    async_remove_recording_index,
    async_start_recording_media_sync,
)
from .playback import async_register_playback_view

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

OBSOLETE_SENSOR_KEYS: tuple[str, ...] = (
    "serial_number",
    "station_sn",
    "device_sn",
    "language_count",
    "language_index",
    "device_mac",
    "mac",
    "bluetooth_mac",
    "online_time",
    "software_version",
    "sw_version",
    "sbs50_sw",
    "alarm_vol",
    "voice_vol",
    "chirp_vol",
    "reminder_vol",
    "camera_recording_resolution",
    "camera_default_codec",
    "camera_video_seconds",
    "camera_alarm_seconds",
    "camera_motion_sensitivity",
    "camera_night_vision_mode",
    "camera_language",
    "camera_antiflicker_rate",
    "camera_motion_tracking_mode",
    "camera_doorbell_ring_key",
    "camera_auto_power_on_capacity",
    "camera_alarm_volume",
    "camera_voice_volume",
    "camera_live_speaker_volume",
    "camera_night_threshold",
    "camera_cry_detection_level",
    "camera_cooldown",
    "camera_mechanical_ding_dong_duration",
    "camera_model",
    "camera_device_status",
    "camera_sleep_message",
    "camera_wake_time",
    "camera_stream_protocol",
    "camera_codec",
    "camera_time_zone",
    "last_ai_detection",
    "last_person_detection_time",
    "last_pet_detection_time",
    "last_vehicle_detection_time",
    "last_package_detection_time",
    "last_other_detection_time",
    "last_vehicle_enter_detection_time",
    "last_vehicle_out_detection_time",
    "last_vehicle_held_up_detection_time",
    "last_package_drop_off_detection_time",
    "last_package_pick_up_detection_time",
    "last_package_exist_detection_time",
    "last_motion_time",
    "led_brightness",
    "await_brightness",
    "trigger_brightness",
    "temperature_min",
    "temperature_max",
    "humidity_min",
    "humidity_max",
    "temperature_unit",
    "temperature_adjustment",
    "humidity_adjustment",
    "temperature_comfort",
    "humidity_comfort",
    "temperature_range",
    "humidity_range",
    "comfort_type",
    "alarm_tone",
    "chirp_tone",
    "reminder_tone",
    "alarm_interval",
    "reminder_time",
    "detection_sensitivity",
    "sensitivity",
    "pir_time",
    "warning_period",
    "app_time",
    "light_scene",
)


OBSOLETE_BINARY_SENSOR_KEYS: tuple[str, ...] = (
    "led_light",
    "motion_required",
    "video_recording_enabled",
    "night_vision_enabled",
    "recording_light_enabled",
    "camera_alarm_enabled",
    "camera_mirror_flip",
    "camera_antiflicker",
    "camera_live_audio",
    "camera_voice_volume",
    "camera_cooldown_enabled",
    "camera_awake",
    "camera_webrtc_supported",
    "person_detected",
    "pet_detected",
    "vehicle_detected",
    "package_detected",
    "other_detected",
    "vehicle_enter_detected",
    "vehicle_out_detected",
    "vehicle_held_up_detected",
    "package_drop_off_detected",
    "package_pick_up_detected",
    "package_exist_detected",
    "alarm_enabled",
    "continued_alarm",
    "on",
    "await_enabled",
    "pir_enabled",
    "sunshine_enabled",
    "key_sound_enabled",
    "warning_enabled",
    "chirp_tone_enabled",
    "reminder_enabled",
    "reminder_tone_enabled",
)

OBSOLETE_SWITCH_KEYS: tuple[str, ...] = ()

OBSOLETE_SELECT_KEYS: tuple[str, ...] = ()

OBSOLETE_NUMBER_KEYS: tuple[str, ...] = ()

OBSOLETE_ENTITY_KEYS_BY_DOMAIN = {
    Platform.SENSOR: OBSOLETE_SENSOR_KEYS,
    Platform.BINARY_SENSOR: OBSOLETE_BINARY_SENSOR_KEYS,
    Platform.SWITCH: OBSOLETE_SWITCH_KEYS,
    Platform.SELECT: OBSOLETE_SELECT_KEYS,
    Platform.NUMBER: OBSOLETE_NUMBER_KEYS,
}

OBSOLETE_ENTITY_SUFFIXES_BY_DOMAIN = {
    domain: tuple(f"-{key.replace('_', '-')}" for key in keys)
    for domain, keys in OBSOLETE_ENTITY_KEYS_BY_DOMAIN.items()
}

OBSOLETE_ACTION_KEYS_BY_DEVICE_TYPE = {
    "XS03-iWX": ("mute",),
}

def _sensor_unique_id(entity_id: str, key: str) -> str:
    """Return the unique ID format used by X-Sense sensor entities."""
    return f"{entity_id}-{key}".replace("_", "-").lower()


def _obsolete_sensor_unique_ids(data) -> set[str]:
    """Return obsolete static diagnostic sensor unique IDs from old releases."""
    unique_ids: set[str] = set()
    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        unique_ids.update(
            _sensor_unique_id(entity.entity_id, key) for key in OBSOLETE_SENSOR_KEYS
        )
    return unique_ids


def _obsolete_action_unique_ids(data) -> set[str]:
    """Return obsolete action entity unique IDs for specific device models."""
    unique_ids: set[str] = set()
    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        for key in OBSOLETE_ACTION_KEYS_BY_DEVICE_TYPE.get(
            getattr(entity, "type", None), ()
        ):
            unique_ids.add(_sensor_unique_id(entity.entity_id, key))
    return unique_ids


def _obsolete_camera_motion_unique_ids(data) -> set[str]:
    """Return old camera binary motion unique IDs now replaced by event entities."""
    unique_ids: set[str] = set()
    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        is_camera = False
        with suppress(AttributeError):
            is_camera = is_camera_entity(entity)
        if is_camera:
            unique_ids.add(_sensor_unique_id(entity.entity_id, "moved"))
    return unique_ids


def _disabled_camera_ai_detection_unique_ids(data) -> set[str]:
    """Return AI Detection event unique IDs for cameras without APK AI services."""
    disabled_unique_ids, _enabled_unique_ids = (
        _camera_ai_detection_unique_ids_by_service_state(data)
    )
    return disabled_unique_ids


def _camera_ai_detection_unique_ids_by_service_state(data) -> tuple[set[str], set[str]]:
    """Return AI Detection unique IDs grouped by APK AI service availability."""
    service_state_by_unique_id: dict[str, bool] = {}
    unknown_unique_ids: set[str] = set()
    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        is_camera = False
        with suppress(AttributeError):
            is_camera = is_camera_entity(entity)
        entity_data = getattr(entity, "data", {})
        if not is_camera or not isinstance(entity_data, dict):
            continue
        unique_id = _sensor_unique_id(entity.entity_id, "ai_detection")
        available = entity_data.get(CAMERA_AI_SERVICE_AVAILABLE)
        if available is True:
            service_state_by_unique_id[unique_id] = True
            unknown_unique_ids.discard(unique_id)
        elif available is False and service_state_by_unique_id.get(unique_id) is not True:
            service_state_by_unique_id[unique_id] = False
            unknown_unique_ids.discard(unique_id)
        elif available is None and unique_id not in service_state_by_unique_id:
            unknown_unique_ids.add(unique_id)

    unique_ids: set[str] = set()
    enabled_unique_ids: set[str] = set()
    for unique_id, available in service_state_by_unique_id.items():
        if available:
            enabled_unique_ids.add(unique_id)
        elif unique_id not in unknown_unique_ids:
            unique_ids.add(unique_id)
    return unique_ids, enabled_unique_ids


def _obsolete_unique_id_suffixes(keys: tuple[str, ...]) -> set[str]:
    """Return old unique ID suffixes independent of the device prefix."""
    return {f"-{key.replace('_', '-')}" for key in keys}


def _registry_entry_domain(registry_entry) -> str:
    """Return a registry entry domain from the stable entity ID shape."""
    entity_id = getattr(registry_entry, "entity_id", "")
    if "." in entity_id:
        return entity_id.split(".", 1)[0]
    return str(getattr(registry_entry, "domain", ""))


def _registry_entry_unique_id(registry_entry) -> str:
    """Return the registry unique ID as a string."""
    return str(getattr(registry_entry, "unique_id", ""))


def _is_obsolete_sensor_entry(registry_entry) -> bool:
    """Return whether a registry entry is an obsolete X-Sense sensor."""
    unique_id = _registry_entry_unique_id(registry_entry)
    return (
        _registry_entry_domain(registry_entry) == Platform.SENSOR
        and getattr(registry_entry, "platform", None) == DOMAIN
        and any(
            unique_id.endswith(suffix)
            for suffix in OBSOLETE_ENTITY_SUFFIXES_BY_DOMAIN[Platform.SENSOR]
        )
    )


def _is_obsolete_binary_sensor_entry(registry_entry) -> bool:
    """Return whether a registry entry is an obsolete X-Sense binary sensor."""
    unique_id = _registry_entry_unique_id(registry_entry)
    return (
        _registry_entry_domain(registry_entry) == Platform.BINARY_SENSOR
        and getattr(registry_entry, "platform", None) == DOMAIN
        and any(
            unique_id.endswith(suffix)
            for suffix in OBSOLETE_ENTITY_SUFFIXES_BY_DOMAIN[Platform.BINARY_SENSOR]
        )
    )


def _is_obsolete_entity_entry(registry_entry) -> bool:
    """Return whether a registry entry is an obsolete X-Sense entity."""
    domain = _registry_entry_domain(registry_entry)
    keys = OBSOLETE_ENTITY_KEYS_BY_DOMAIN.get(domain)
    if keys is None:
        return False
    unique_id = _registry_entry_unique_id(registry_entry)
    return (
        getattr(registry_entry, "platform", None) == DOMAIN
        and any(
            unique_id.endswith(suffix)
            for suffix in OBSOLETE_ENTITY_SUFFIXES_BY_DOMAIN[domain]
        )
    )


def _remove_obsolete_sensor_entities(
    hass: HomeAssistant, data, entry: ConfigEntry
) -> None:
    """Remove old serial/MAC diagnostic sensors from prior releases."""
    entity_registry = er.async_get(hass)
    checked_unique_ids = set()
    obsolete_action_unique_ids = _obsolete_action_unique_ids(data)
    obsolete_camera_motion_unique_ids = _obsolete_camera_motion_unique_ids(data)
    (
        disabled_camera_ai_detection_unique_ids,
        enabled_camera_ai_detection_unique_ids,
    ) = (
        _camera_ai_detection_unique_ids_by_service_state(data)
    )

    seen_entity_ids = set()
    registry_entries = list(
        er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    )
    registry_entries.extend(getattr(entity_registry, "entities", {}).values())

    for registry_entry in registry_entries:
        if registry_entry.entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(registry_entry.entity_id)
        checked_unique_ids.add(registry_entry.unique_id)
        if _is_obsolete_entity_entry(registry_entry) or (
            _registry_entry_domain(registry_entry) == Platform.BUTTON
            and getattr(registry_entry, "platform", None) == DOMAIN
            and _registry_entry_unique_id(registry_entry)
            in obsolete_action_unique_ids
        ) or (
            _registry_entry_domain(registry_entry) == Platform.BINARY_SENSOR
            and getattr(registry_entry, "platform", None) == DOMAIN
            and _registry_entry_unique_id(registry_entry)
            in obsolete_camera_motion_unique_ids
        ):
            entity_registry.async_remove(registry_entry.entity_id)
        elif (
            _registry_entry_domain(registry_entry) == Platform.EVENT
            and getattr(registry_entry, "platform", None) == DOMAIN
            and _registry_entry_unique_id(registry_entry)
            in disabled_camera_ai_detection_unique_ids
            and getattr(registry_entry, "disabled_by", None) is None
        ):
            entity_registry.async_update_entity(
                registry_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )
        elif (
            _registry_entry_domain(registry_entry) == Platform.EVENT
            and getattr(registry_entry, "platform", None) == DOMAIN
            and _registry_entry_unique_id(registry_entry)
            in enabled_camera_ai_detection_unique_ids
            and getattr(registry_entry, "disabled_by", None)
            == er.RegistryEntryDisabler.INTEGRATION
        ):
            entity_registry.async_update_entity(
                registry_entry.entity_id,
                disabled_by=None,
            )

    for unique_id in _obsolete_sensor_unique_ids(data) - checked_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, unique_id
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)

    for unique_id in obsolete_action_unique_ids - checked_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.BUTTON, DOMAIN, unique_id
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)

    for unique_id in obsolete_camera_motion_unique_ids - checked_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.BINARY_SENSOR, DOMAIN, unique_id
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)

    for unique_id in disabled_camera_ai_detection_unique_ids - checked_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.EVENT, DOMAIN, unique_id
        )
        if entity_id is not None:
            entity_registry.async_update_entity(
                entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )

    for unique_id in enabled_camera_ai_detection_unique_ids - checked_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.EVENT, DOMAIN, unique_id
        )
        if entity_id is not None:
            registry_entry = entity_registry.async_get(entity_id)
            if (
                registry_entry is not None
                and getattr(registry_entry, "disabled_by", None)
                == er.RegistryEntryDisabler.INTEGRATION
            ):
                entity_registry.async_update_entity(entity_id, disabled_by=None)


def _legacy_entity_key(registry_entry) -> str | None:
    # Return a usable entity key from legacy registry metadata.
    for value in (
        getattr(registry_entry, "object_id_base", None),
        getattr(registry_entry, "original_name", None),
        getattr(registry_entry, "translation_key", None),
    ):
        if value:
            return str(value)

    unique_id = getattr(registry_entry, "unique_id", "")
    if "-" in unique_id:
        return unique_id.rsplit("-", 1)[1]

    return None


def _legacy_device_name(device, entity_id: str) -> str | None:
    # Return the stable visible name for a legacy registry device.
    if device is not None:
        for value in (
            getattr(device, "name_by_user", None),
            getattr(device, "name", None),
        ):
            if value:
                return str(value)

    object_id = entity_id.split(".", 1)[-1]
    if object_id.endswith("_none"):
        return object_id[: -len("_none")]

    return None


def _legacy_none_entity_target(
    entity_registry, device_registry, registry_entry
) -> str | None:
    # Return the clean entity ID for an old *_none entity when safe.
    entity_id = getattr(registry_entry, "entity_id", "")
    if (
        not entity_id.endswith("_none")
        or getattr(registry_entry, "platform", None) != DOMAIN
    ):
        return None

    device_id = getattr(registry_entry, "device_id", None)
    device = device_registry.async_get(device_id) if device_id else None
    device_name = _legacy_device_name(device, entity_id)
    key = _legacy_entity_key(registry_entry)
    if not device_name or not key:
        return None

    domain = entity_id.split(".", 1)[0]
    object_id = slugify(f"{device_name} {key}")
    if not domain or not object_id:
        return None

    new_entity_id = f"{domain}.{object_id}"
    if new_entity_id == entity_id:
        return None

    existing_entry = entity_registry.async_get(new_entity_id)
    if (
        existing_entry is not None
        and getattr(existing_entry, "entity_id", None) != entity_id
    ):
        return None

    return new_entity_id


def _migrate_legacy_none_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Rename old *_none entity IDs left by earlier releases.
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    seen_entity_ids = set()
    registry_entries = list(
        er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    )
    registry_entries.extend(getattr(entity_registry, "entities", {}).values())

    for registry_entry in registry_entries:
        if registry_entry.entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(registry_entry.entity_id)
        new_entity_id = _legacy_none_entity_target(
            entity_registry, device_registry, registry_entry
        )
        if new_entity_id is not None:
            entity_registry.async_update_entity(
                registry_entry.entity_id, new_entity_id=new_entity_id
            )


def _visible_identifier_connections_removed(connections):
    """Return device connections without visible static hardware identifiers."""
    return {
        connection
        for connection in connections
        if connection[0] not in {CONNECTION_BLUETOOTH, CONNECTION_NETWORK_MAC}
    }


def _clear_visible_device_metadata(device_registry, device) -> None:
    """Clear old visible serial/MAC metadata from one registry device."""
    new_connections = _visible_identifier_connections_removed(device.connections)
    if device.serial_number is None and new_connections == device.connections:
        return

    device_registry.async_update_device(
        device.id,
        new_connections=new_connections,
        serial_number=None,
    )


def _remove_obsolete_device_metadata(
    hass: HomeAssistant, data, entry: ConfigEntry
) -> None:
    """Clear old serial/MAC metadata from existing device registry entries."""
    device_registry = dr.async_get(hass)
    checked_device_ids = set()

    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        checked_device_ids.add(device.id)
        _clear_visible_device_metadata(device_registry, device)

    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, entity.entity_id)}
        )
        if device is None or device.id in checked_device_ids:
            continue

        _clear_visible_device_metadata(device_registry, device)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up X-Sense Home Security from a config entry."""
    coordinator = XSenseDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    _remove_obsolete_sensor_entities(hass, coordinator.data, entry)
    _remove_obsolete_device_metadata(hass, coordinator.data, entry)
    _migrate_legacy_none_entity_ids(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_register_playback_view(hass)
    await async_register_recording_services(hass)
    async_start_recording_media_sync(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_camera_ai_history_polling()

    _remove_obsolete_sensor_entities(hass, coordinator.data, entry)

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: XSenseDataUpdateCoordinator | None = hass.data[DOMAIN].pop(
            entry.entry_id, None
        )
        async_remove_recording_index(hass, entry.entry_id)
        if coordinator is not None:
            await coordinator.async_shutdown()

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow users to remove XSense devices no longer returned by the cloud API."""
    coordinator: XSenseDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is None:
        return False

    data = coordinator.data
    if not data:
        return False

    current_identifiers = set()
    for station in data.get("stations", {}).values():
        current_identifiers.add(station.entity_id)
        current_identifiers.add(station.sn)

    for device in data.get("devices", {}).values():
        current_identifiers.add(device.entity_id)
        current_identifiers.add(device.sn)

    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN and identifier[1] in current_identifiers
    )
