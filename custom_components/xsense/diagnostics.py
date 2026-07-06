"""Diagnostics support for XSense."""

from __future__ import annotations

from datetime import datetime, timezone
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

LOCAL_ADDRESS_KEYS = ("ip", "ipAddress")
LOCAL_MAC_KEYS = ("mac", "macBT", "wiredMacAddress")


def _diagnostic_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return compact functional state data for diagnostics."""
    return {
        key: async_redact_data(value, TO_REDACT)
        for key, value in data.items()
        if key in DIAGNOSTIC_DATA_KEYS
    }


def _first_present(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-empty value for the given keys."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def local_communication_diagnostics(entity) -> dict[str, Any]:
    """Return a non-invasive summary of local communication evidence.

    X-Sense devices may report LAN-facing fields such as IP address, SSID, or
    MAC address while still using AWS IoT shadows for normal runtime control.
    This summary records the evidence without claiming local control exists.
    """
    data = getattr(entity, "data", {}) or {}
    ip_address = _first_present(data, LOCAL_ADDRESS_KEYS)
    ssid = data.get("ssid")
    mac_reported = any(data.get(key) not in (None, "") for key in LOCAL_MAC_KEYS)
    shadow_name = getattr(entity, "shadow_name", None)

    return {
        "ip_reported": bool(ip_address),
        "ssid_reported": bool(ssid),
        "mac_reported": mac_reported,
        "local_runtime_candidate": bool(ip_address or ssid or mac_reported),
        "local_control_confirmed": False,
        "runtime_path": "aws_iot_shadow",
        "shadow_name": shadow_name,
    }


def _expiry_diagnostics(value) -> dict[str, Any]:
    """Return safe token-expiry diagnostics without exposing token values."""
    if value is None:
        return {"present": False, "expired": None, "seconds_remaining": None}
    if not isinstance(value, datetime):
        return {"present": True, "expired": None, "seconds_remaining": None}
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    now = datetime.now(value.tzinfo)
    seconds_remaining = int((value - now).total_seconds())
    return {
        "present": True,
        "expired": seconds_remaining <= 0,
        "seconds_remaining": seconds_remaining,
    }


def api_client_diagnostics(xsense) -> dict[str, Any]:
    """Return non-secret API client state for support diagnostics."""
    if xsense is None:
        return {"connected": False}

    addx_session = getattr(xsense, "_addx_session", None)
    if not isinstance(addx_session, dict):
        addx_session = {}

    return {
        "connected": True,
        "app_version": getattr(xsense, "VERSION", None),
        "app_code": getattr(xsense, "APPCODE", None),
        "client_type": getattr(xsense, "CLIENTYPE", None),
        "ipc_app_version": getattr(xsense, "IPC_VERSION", None),
        "ipc_app_code": getattr(xsense, "IPC_APPCODE", None),
        "ipc_client_type": getattr(xsense, "IPC_CLIENTTYPE", None),
        "region_present": bool(getattr(xsense, "region", None)),
        "user_id_present": bool(getattr(xsense, "userid", None)),
        "user_id_code_present": bool(getattr(xsense, "user_id_code", None)),
        "aws_signer_present": bool(getattr(xsense, "signer", None)),
        "access_token": _expiry_diagnostics(
            getattr(xsense, "access_token_expiry", None)
        ),
        "aws_token": _expiry_diagnostics(getattr(xsense, "aws_access_expiry", None)),
        "addx_session_present": bool(addx_session),
        "addx_node_type": addx_session.get("nodeType"),
        "house_count": len(getattr(xsense, "houses", {}) or {}),
    }


def entity_diagnostics(entity) -> dict[str, Any]:
    """Return diagnostic data for an X-Sense entity."""
    return {
        "type": entity.type,
        "entity_type": str(getattr(entity, "entity_type", "")),
        "online": getattr(entity, "online", None),
        "communication": local_communication_diagnostics(entity),
        "data": _diagnostic_data(getattr(entity, "data", {})),
    }


def _type_counts(entities) -> dict[str, int]:
    """Return compact type counts for diagnostics."""
    counts: dict[str, int] = {}
    for entity in entities:
        entity_type = str(getattr(entity, "type", "") or "unknown")
        counts[entity_type] = counts.get(entity_type, 0) + 1
    return dict(sorted(counts.items()))


def _communication_counts(entities) -> dict[str, int]:
    """Return compact local/cloud communication evidence counts."""
    counts = {
        "local_runtime_candidates": 0,
        "local_control_confirmed": 0,
        "aws_iot_shadow": 0,
    }
    for entity in entities:
        communication = local_communication_diagnostics(entity)
        if communication["local_runtime_candidate"]:
            counts["local_runtime_candidates"] += 1
        if communication["local_control_confirmed"]:
            counts["local_control_confirmed"] += 1
        if communication["runtime_path"] == "aws_iot_shadow":
            counts["aws_iot_shadow"] += 1
    return counts


def coordinator_diagnostics(
    coordinator: XSenseDataUpdateCoordinator,
) -> dict[str, Any]:
    """Return compact coordinator state for future support reports."""
    stations = (coordinator.data or {}).get("stations", {})
    devices = (coordinator.data or {}).get("devices", {})
    all_entities = [*stations.values(), *devices.values()]
    last_camera_update = coordinator._last_camera_update_attempt
    return {
        "api": api_client_diagnostics(getattr(coordinator, "xsense", None)),
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
        "mqtt_servers": {
            server: {
                "connected": mqtt.connected,
                "subscriptions": len(
                    getattr(mqtt, "_simple_subscriptions", {})
                )
                + len(getattr(mqtt, "_wildcard_subscriptions", set())),
            }
            for server, mqtt in sorted(coordinator.mqtt_servers.items())
        },
        "station_count": len(stations),
        "device_count": len(devices),
        "station_types": _type_counts(stations.values()),
        "device_types": _type_counts(devices.values()),
        "communication": _communication_counts(all_entities),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    stations = data.get("stations", {})
    devices = data.get("devices", {})

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": coordinator_diagnostics(coordinator),
        "data": {
            "stations": [entity_diagnostics(station) for station in stations.values()],
            "devices": [entity_diagnostics(device) for device in devices.values()],
        },
    }
