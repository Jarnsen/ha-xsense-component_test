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


def bool_state(value: typing.Any) -> bool:
    if isinstance(value, str):
        return value == "1"
    return bool(value)


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
    "alarmSound": bool_state,
    "appTip": bool_state,
    "awaitEnable": bool_state,
    "baseRemove": bool_state,
    "continuedAlarm": bool_state,
    "continueAlarm": bool_state,
    "acBreak": bool_state,
    "bEndUse": bool_state,
    "isActivate": bool_state,
    "initiativeAlarm": bool_state,
    "isAlarm": bool_state,
    "isArmed": bool_state,
    "isFireDrill": bool_state,
    "isMoved": bool_state,
    "keySound": bool_state,
    "mailNotice": bool_state,
    "mute": bool_state,
    "muteStatus": bool_state,
    "needMotion": bool_state,
    "on": bool_state,
    "pirEnable": bool_state,
    "remindOn": bool_state,
    "remindToneEnable": bool_state,
    "scheduleTip": bool_state,
    "sunshineEnable": bool_state,
    "tempAlarmStatus": bool_state,
    "tempMuteStatus": bool_state,
    "test": bool_state,
    "timeZoneEnabled": bool_state,
    "timeZoneValid": bool_state,
    "usbCharge": bool_state,
    "waterAlarmStatus": bool_state,
    "waterMuteStatus": bool_state,
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
    "awaitBrightness": safe_int,
    "voiceVol": safe_int,
    "chirpVol": safe_int,
    "isCharging": safe_int,
    "languageCount": safe_int,
    "languageIndex": safe_int,
    "ledBrt": safe_int,
    "pirInterval": safe_int,
    "pirSensitivity": safe_int,
    "remindVol": safe_int,
    "triggerBrightness": safe_int,
    "wifiRssiLevel": safe_int,
}


def map_type(k: str, value: typing.Any):
    return type_mapping[k](value) if k in type_mapping else value


def map_values(device_type: str, data: typing.Dict):
    mapping = property_mapper.get("*", {}) | property_mapper.get(device_type, {})

    return {mapping.get(k, k): map_type(mapping.get(k, k), v) for k, v in data.items()}
