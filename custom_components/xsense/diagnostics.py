"""Diagnostics support for XSense."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "adminId",
    "cameraLiveId",
    "deviceId",
    "ipcId",
    "ipcSn",
    "networkName",
    "stationId",
    "thumbImgUrl",
    "title",
    "unique_id",
    "userId",
}

DIAGNOSTIC_DATA_KEYS = {
    "alarmEnable",
    "alarmEnabled",
    "alarmInterval",
    "alarmOccur",
    "alarmSeconds",
    "alarmSource",
    "alarmStatus",
    "alarmTone",
    "alarmVol",
    "antiflicker",
    "antiflickerSwitch",
    "awaitEnable",
    "batInfo",
    "cameraAudioUrl",
    "cameraLiveProtocol",
    "cameraLiveUrl",
    "category",
    "chargeAutoPowerOnSwitch",
    "chirpToneEnable",
    "continueAlarm",
    "continuedAlarm",
    "cooldownEnabled",
    "cooldownSupported",
    "cooldownValue",
    "cryDetect",
    "cryDetectLevel",
    "deviceCallToggleOn",
    "deviceDormancyMessage",
    "deviceDormancyWakeTime",
    "devicePersonDetect",
    "deviceStatus",
    "firmwareStatus",
    "firmwareVersion",
    "ip",
    "ipAddress",
    "keySound",
    "lastSelfTest",
    "lastSelfTestTime",
    "ledLight",
    "liveAudioToggleOn",
    "liveSpeakerVolume",
    "mechanicalDingDongDuration",
    "mechanicalDingDongSwitch",
    "mirrorFlip",
    "motionTrack",
    "motionTrackMode",
    "mute",
    "muteStatus",
    "needAlarm",
    "needMotion",
    "needNightVision",
    "needVideo",
    "on",
    "pirEnable",
    "recLamp",
    "recResolution",
    "recordingAudioToggleOn",
    "remindOn",
    "remindToneEnable",
    "rfLevel",
    "safeMode",
    "signalStrength",
    "ssid",
    "supportAlarm",
    "supportAlarmVolume",
    "supportAntiFlicker",
    "supportChargeAutoPowerOn",
    "supportCryDetect",
    "supportDeviceCall",
    "supportDoorBellAlarm",
    "supportLight",
    "supportLiveAudio",
    "supportLiveSpeakerVolume",
    "supportMechanicalDingDong",
    "supportMirrorFlip",
    "supportMotionTrack",
    "supportPirCooldown",
    "supportRecLamp",
    "supportRecordingAudio",
    "supportSleep",
    "supportVoiceVolume",
    "supportWebrtc",
    "supportedRecordingResolutions",
    "temperature",
    "time",
    "voiceVol",
    "voiceVolumeSwitch",
    "waterAlarmStatus",
    "waterMuteStatus",
    "whiteLightScintillation",
    "wifiRSSI",
}


def _diagnostic_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return compact functional state data for diagnostics."""
    return {
        key: async_redact_data(value, TO_REDACT)
        for key, value in data.items()
        if key in DIAGNOSTIC_DATA_KEYS
    }


def entity_diagnostics(entity) -> dict[str, Any]:
    """Return diagnostic data for an X-Sense entity."""
    return {
        "type": entity.type,
        "entity_type": str(getattr(entity, "entity_type", "")),
        "online": getattr(entity, "online", None),
        "data": _diagnostic_data(getattr(entity, "data", {})),
    }


def _type_counts(entities) -> dict[str, int]:
    """Return compact type counts for diagnostics."""
    counts: dict[str, int] = {}
    for entity in entities:
        entity_type = str(getattr(entity, "type", "") or "unknown")
        counts[entity_type] = counts.get(entity_type, 0) + 1
    return dict(sorted(counts.items()))


def coordinator_diagnostics(
    coordinator: XSenseDataUpdateCoordinator,
) -> dict[str, Any]:
    """Return compact coordinator state for future support reports."""
    stations = (coordinator.data or {}).get("stations", {})
    devices = (coordinator.data or {}).get("devices", {})
    last_camera_update = coordinator._last_camera_update_attempt
    return {
        "last_update_success": coordinator.last_update_success,
        "last_exception": (
            type(coordinator.last_exception).__name__
            if coordinator.last_exception
            else None
        ),
        "initialized": coordinator._initialized,
        "camera_initialized": coordinator._camera_initialized,
        "last_camera_update_attempt": (
            last_camera_update.isoformat() if last_camera_update else None
        ),
        "camera_station_cache_count": len(coordinator._camera_station_cache),
        "mqtt_server_count": len(coordinator.mqtt_servers),
        "mqtt_connected_count": sum(
            1 for mqtt in coordinator.mqtt_servers.values() if mqtt.connected
        ),
        "station_count": len(stations),
        "device_count": len(devices),
        "station_types": _type_counts(stations.values()),
        "device_types": _type_counts(devices.values()),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": coordinator_diagnostics(coordinator),
        "data": {
            "stations": [
                entity_diagnostics(station)
                for station in coordinator.data["stations"].values()
            ],
            "devices": [
                entity_diagnostics(device)
                for device in coordinator.data["devices"].values()
            ],
        },
    }
