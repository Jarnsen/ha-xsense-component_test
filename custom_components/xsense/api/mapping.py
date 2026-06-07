from collections.abc import Callable
import typing

property_mapper = {
    "*": {"wifiRssi": "wifiRSSI"},
    "STH0A": {
        "a": "alarmStatus",
        "b": "temperature",
        "c": "humidity",
        "d": "tempUnit",
        "e": "tRange",
        "f": "hRange",
        "g": "alarmEnabled",
        "h": "continuedAlarm",
        "t": "time",
    },
    "STH0B": {
        "a": "alarmStatus",
        "b": "temperature",
        "c": "humidity",
        "d": "tempUnit",
        "e": "tRange",
        "f": "hRange",
        "g": "alarmEnabled",
        "h": "continuedAlarm",
        "t": "time",
    },
    "STH51": {
        "a": "alarmStatus",
        "b": "temperature",
        "c": "humidity",
        "d": "tempUnit",
        "e": "tRange",
        "f": "hRange",
        "g": "alarmEnabled",
        "h": "continuedAlarm",
        "t": "time",
    },
}


def bool_state(value: typing.Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on"}:
            return True
        if normalized in {"0", "false", "off"}:
            return False
    return None


def safe_float(value: typing.Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: typing.Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


type_mapping: dict[str, Callable[[typing.Any], typing.Any]] = {
    "batInfo": safe_int,
    "rfLevel": safe_int,
    "wifiRSSI": safe_int,
    "alarmStatus": bool_state,
    "alarmEnabled": bool_state,
    "alarmEnable": bool_state,
    "alarmWhenRemoveToggleOn": bool_state,
    "activate": bool_state,
    "alarmSound": bool_state,
    "appTip": bool_state,
    "awaitEnable": bool_state,
    "antiflickerSupport": bool_state,
    "antiflickerSwitch": bool_state,
    "baseRemove": bool_state,
    "continuedAlarm": bool_state,
    "continueAlarm": bool_state,
    "cooldownEnabled": bool_state,
    "cooldownSupported": bool_state,
    "acBreak": bool_state,
    "bEndUse": bool_state,
    "deviceCallToggleOn": bool_state,
    "isActivate": bool_state,
    "isAdmin": bool_state,
    "initiativeAlarm": bool_state,
    "isAlarm": bool_state,
    "isArmed": bool_state,
    "isFireDrill": bool_state,
    "isMoved": bool_state,
    "keySound": bool_state,
    "liveAudioToggleOn": bool_state,
    "mailNotice": bool_state,
    "mechanicalDingDongSwitch": bool_state,
    "mirrorFlip": bool_state,
    "mute": bool_state,
    "muteStatus": bool_state,
    "needAlarm": bool_state,
    "needMotion": bool_state,
    "needNightVision": bool_state,
    "needVideo": bool_state,
    "on": bool_state,
    "pirEnable": bool_state,
    "recordingAudioToggleOn": bool_state,
    "recLamp": bool_state,
    "remindOn": bool_state,
    "remindToneEnable": bool_state,
    "scheduleTip": bool_state,
    "showCodecChange": bool_state,
    "sunshineEnable": bool_state,
    "tempAlarmStatus": bool_state,
    "tempMuteStatus": bool_state,
    "test": bool_state,
    "timeZoneEnabled": bool_state,
    "timeZoneValid": bool_state,
    "usbCharge": bool_state,
    "voiceVolumeSwitch": bool_state,
    "waterAlarmStatus": bool_state,
    "waterMuteStatus": bool_state,
    "whiteLightScintillation": bool_state,
    "warnIsOpen": bool_state,
    "chirpToneEnable": bool_state,
    "coPpm": safe_int,
    "coPpmPeak": safe_int,
    "warnLongCoPpm": safe_int,
    "warnShortCoPpm": safe_int,
    "coLevel": safe_int,
    "isLifeEnd": bool_state,
    "temperature": safe_float,
    "humidity": safe_float,
    "tempRangeMin": safe_float,
    "tempRangeMax": safe_float,
    "humRangeMin": safe_float,
    "humRangeMax": safe_float,
    "hAdjust": safe_float,
    "hComfort": safe_float,
    "tAdjust": safe_float,
    "tComfort": safe_float,
    "alarmVol": safe_int,
    "alarmSeconds": safe_int,
    "awaitBrightness": safe_int,
    "awake": safe_int,
    "batteryLevel": safe_int,
    "cameraStatusCode": safe_int,
    "chargeAutoPowerOnCapacity": safe_int,
    "chargeAutoPowerOnSwitch": safe_int,
    "cooldownValue": safe_int,
    "cryDetect": safe_int,
    "cryDetectLevel": safe_int,
    "devicePersonDetect": safe_int,
    "deviceDormancyWakeTime": safe_int,
    "deviceStatus": safe_int,
    "firmwareStatus": safe_int,
    "voiceVol": safe_int,
    "chirpVol": safe_int,
    "isCharging": safe_int,
    "languageCount": safe_int,
    "languageIndex": safe_int,
    "ledBrt": safe_int,
    "liveSpeakerVolume": safe_int,
    "mechanicalDingDongDuration": safe_int,
    "motionSensitivity": safe_int,
    "motionTrack": bool_state,
    "motionTrackMode": safe_int,
    "nightThresholdLevel": safe_int,
    "nightVisionMode": safe_int,
    "pirInterval": safe_int,
    "pirSensitivity": safe_int,
    "sdCardFormatStatus": safe_int,
    "sdCardTotal": safe_int,
    "sdCardUsed": safe_int,
    "remindVol": safe_int,
    "signalStrength": safe_int,
    "supportLiveAudio": bool_state,
    "supportLiveSpeakerVolume": bool_state,
    "supportAlarm": bool_state,
    "supportAlarmVolume": bool_state,
    "supportAntiFlicker": bool_state,
    "supportBattery": bool_state,
    "supportChargeAutoPowerOn": bool_state,
    "supportCryDetect": bool_state,
    "supportDeviceCall": bool_state,
    "supportDoorBellAlarm": bool_state,
    "supportLight": bool_state,
    "supportMechanicalDingDong": bool_state,
    "supportMirrorFlip": bool_state,
    "supportMotionTrack": bool_state,
    "supportPirCooldown": bool_state,
    "supportRecLamp": bool_state,
    "supportRecordingAudio": bool_state,
    "supportRocker": bool_state,
    "supportSdCard": bool_state,
    "supportSleep": bool_state,
    "supportVoiceVolume": bool_state,
    "supportWebrtc": bool_state,
    "thumbImgTime": safe_int,
    "triggerBrightness": safe_int,
    "videoSeconds": safe_int,
    "wifiRssiLevel": safe_int,
}


def map_type(k: str, value: typing.Any):
    return type_mapping[k](value) if k in type_mapping else value


def map_values(device_type: str, data: typing.Dict):
    mapping = property_mapper.get("*", {}) | property_mapper.get(device_type, {})

    return {mapping.get(k, k): map_type(mapping.get(k, k), v) for k, v in data.items()}
