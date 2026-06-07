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


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
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
