from enum import Enum
from typing import Callable, Dict, Optional, Union


class EntityType(Enum):
    ALARM = "alarm"
    BASE = "base"
    BASESTATION = "station"
    CAMERA = "camera"
    CO = "co"
    COMBI = "combi"
    DOOR = "door"
    HEAT = "heat"
    KEYPAD = "keypad"
    LIGHT = "light"
    LISTENER = "listener"
    MAILBOX = "mailbox"
    MOTION = "motion"
    RADON = "radon"
    REMOTE = "remote"
    SMARTDROP = "smartdrop"
    SMOKE = "smoke"
    TEMPERATURE = "temperature"
    WATER = "water"


def MuteAction(
    shadow: Union[str, Callable] = "appMute",
    topic: Union[str, Callable, None] = "2nd_appmute",
    extra: Optional[Dict] = None,
    mute_type: Optional[str] = None,
    target=None,
):
    data = {
        "action": "mute",
        "topic": topic,
        "shadow": shadow,
    }
    if extra:
        data["extra"] = extra
    if mute_type is not None:
        data.setdefault("extra", {})["muteType"] = mute_type
    if target:
        data["target"] = target

    return data


def TestAction(shadow="appSelfTest", extra: Optional[Dict] = None, target=None):
    data = {
        "action": "test",
        "topic": lambda x: f"2nd_selftest_{x.sn}",
        "shadow": shadow,
        "time_format": "epoch_ms",
    }
    if extra:
        data["extra"] = extra
    if target:
        data["target"] = target
    return data


def SBS50SecondGenTestAction():
    return TestAction("app2ndSelfTest", extra={"userParam": "source=1"})


def XP0JTestAction():
    return TestAction(
        "app2ndSelfTest",
        extra={"userParam": "source=1"},
        target=lambda entity: _ThingTarget(entity, f"SBS50{entity.sn}"),
    )


def _smoke_rf_test_shadow(entity) -> str:
    return "app2ndSelfTest" if _is_smoke_v9(entity) else "appSelfTest"


def _smoke_rf_test_target(entity):
    station = getattr(entity, "station", entity)
    if _is_smoke_v9(entity) or getattr(station, "type", None) == "SBS50":
        return station
    return _ThingTarget(station, station.sn)


def _smoke_rf_test_topic(entity):
    station = getattr(entity, "station", entity)
    if _is_smoke_v9(entity) or getattr(station, "type", None) == "SBS50":
        return f"2nd_selftest_{entity.sn}"
    return f"appselftest_{entity.sn}"


def _smoke_rf_test_time_format(entity) -> str | None:
    station = getattr(entity, "station", entity)
    if _is_smoke_v9(entity) or getattr(station, "type", None) == "SBS50":
        return "epoch_ms"
    return None


def _smoke_rf_test_extra(entity) -> Dict:
    station = getattr(entity, "station", entity)
    if _is_smoke_v9(entity) or getattr(station, "type", None) == "SBS50":
        return {"userParam": "source=1"}
    return {}


def SmokeRFTestAction():
    return {
        "action": "test",
        "topic": _smoke_rf_test_topic,
        "shadow": _smoke_rf_test_shadow,
        "extra": _smoke_rf_test_extra,
        "target": _smoke_rf_test_target,
        "time_format": _smoke_rf_test_time_format,
    }


class _ThingTarget:
    def __init__(self, source, shadow_name: str) -> None:
        self.house = getattr(source, "house", None)
        self.shadow_name = shadow_name


def _xs01_wx_thing_name(station_sn: str) -> str:
    separator = "-" if "EN" in station_sn.upper() or "UL" in station_sn.upper() else ""
    return f"XS01-WX{separator}{station_sn}"


def _wifi_thing_name(device_type: str, station_sn: str) -> str:
    if device_type == "XS01-WX":
        return _xs01_wx_thing_name(station_sn)
    if device_type in {"XS0E-iR", "XS03-WX"}:
        return f"{device_type}{station_sn}"
    return f"{device_type}-{station_sn}"


def _wifi_thing_target(entity):
    station = getattr(entity, "station", entity)
    return _ThingTarget(station, _wifi_thing_name(entity.type, station.sn))


_WIFI_FIRE_DRILL_TYPES = {"XP0J-iA", "XS0R-iA"}


def _fire_drill_target(entity):
    if entity.type in _WIFI_FIRE_DRILL_TYPES:
        return _wifi_thing_target(entity)
    return getattr(entity, "station", entity)


def WifiSelfTestAction():
    return TestAction(
        "appSelfTest", extra={"userParam": "source=1"}, target=_wifi_thing_target
    )


def _fire_drill_alarm_type(entity) -> str:
    if entity.type in ("XC01-M", "XC0C-MR"):
        return "2"
    return "1"


def _fire_drill_device_sn(entity) -> str:
    station = getattr(entity, "station", entity)
    return station.sn


def FireDrillAction():
    return {
        "action": "firedrill",
        "topic": "2nd_firedrill",
        "shadow": "appFireDrill",
        "target": _fire_drill_target,
        "data": lambda entity: {
            "alarmTone": "1",
            "alarmType": _fire_drill_alarm_type(entity),
            "alarmVol": "75",
            "deviceSN": _fire_drill_device_sn(entity),
            "drill": "1",
            "drillTime": "30",
            "location": "17",
        },
    }


def SATestAction(shadow="appSelfTest"):
    """Standalone device test."""
    return {
        "action": "test",
        "topic": lambda x: f"appselftest_{x.sn}",
        "shadow": shadow,
        "time_format": None,
    }


def _is_smoke_v9(entity) -> bool:
    try:
        return int(entity.data.get("smokeEdition", 0)) >= 9
    except (TypeError, ValueError):
        return False


def _xs01_wx_target(entity):
    station = getattr(entity, "station", entity)
    return _ThingTarget(station, _xs01_wx_thing_name(station.sn))


def XS01WXMuteAction():
    return MuteAction(
        topic=lambda entity: "2nd_appmute" if _is_smoke_v9(entity) else "appmute",
        target=_xs01_wx_target,
        mute_type="0",
    )


def SC07MRMuteAction():
    return MuteAction(
        shadow=lambda entity: "app2ndMute" if _is_smoke_v9(entity) else "appSc07mrMute",
        mute_type="1",
        extra={"userParam": "source=1"},
    )


def WifiAlarmMuteAction():
    return MuteAction(mute_type="1", target=_wifi_thing_target)


def WifiExtendedMuteAction():
    return MuteAction("extendMute", "2nd_appmute", mute_type="1", target=_wifi_thing_target)


def WifiWaterMuteAction():
    return MuteAction("appWater", "2nd_appwater", mute_type="1", target=_wifi_thing_target)


def SBS50SmokeMuteAction():
    return MuteAction("appMute", "2nd_appmute", mute_type="1")


def SBS50CoMuteAction():
    return MuteAction("app2ndMute", "2nd_appmute", mute_type="1")


def _station_serial_target(entity):
    station = getattr(entity, "station", entity)
    return _ThingTarget(station, station.sn)


def SmokeRFAppMuteAction():
    return MuteAction("appMute", "appmute", target=_station_serial_target, mute_type="1")


entities = {
    "SAL51": {
        "type": EntityType.LISTENER,
        "actions": [
            TestAction("listenerSelfTest"),
            MuteAction("appListener", mute_type="1"),
        ],
    },
    "SAL100": {
        "type": EntityType.LISTENER,
        "actions": [
            TestAction("listenerSelfTest"),
            MuteAction("appListener", mute_type="1"),
        ],
    },
    "SBS10": {
        "type": EntityType.BASESTATION,
    },
    "SBS50": {
        "type": EntityType.BASESTATION,
        "identifier": lambda entity: f"SBS50{entity.sn}",
    },
    "SSC0A": {
        "type": EntityType.CAMERA,
    },
    "SSC0B": {
        "type": EntityType.CAMERA,
    },
    "SC01-MN": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "SC01-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("appSc07mrMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "SC06-WX": {
        "identifier": lambda entity: f"SC06-WX-{entity.sn}",
        "type": EntityType.COMBI,
        "actions": [WifiAlarmMuteAction()],
    },
    "SC07-MR": {
        "identifier": lambda entity: f"SC07-MR-{entity.sn}",
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            SC07MRMuteAction(),
            FireDrillAction(),
        ],
    },
    "SC07-WX": {
        "identifier": lambda entity: f"SC07-WX-{entity.sn}",
        "type": EntityType.COMBI,
        "actions": [WifiAlarmMuteAction()],
    },
    "SD11-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "SD19-MN": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "SDA51": {
        "type": EntityType.ALARM,
        "actions": [
            {
                "action": "mute",
                "topic": "2nd_driveway",
                "shadow": "appDriveway",
                "data": {"mute": "1"},
            },
        ],
    },
    "SDS0A": {
        "type": EntityType.DOOR,
        "actions": [
            SBS50SecondGenTestAction(),
        ],
    },
    "SES01": {
        "type": EntityType.DOOR,
    },
    "SKF01": {
        "type": EntityType.REMOTE,
    },
    "SK0Z-3S": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "SKP01": {
        "type": EntityType.KEYPAD,
    },
    "SKP0A": {
        "type": EntityType.KEYPAD,
        "actions": [
            SBS50SecondGenTestAction(),
        ],
    },
    "SMA51": {
        "type": EntityType.MAILBOX,
        "actions": [
            MuteAction("appMailMute", "2nd_appmailmute", mute_type="1"),
        ],
    },
    "SMS0A": {
        "type": EntityType.MOTION,
        "actions": [
            SBS50SecondGenTestAction(),
        ],
    },
    "SMS01": {
        "type": EntityType.MOTION,
    },
    "SPL51": {
        "type": EntityType.LIGHT,
    },
    "group-L": {
        "type": EntityType.LIGHT,
    },
    "SSD01": {
        "type": EntityType.SMARTDROP,
    },
    "SSL51": {
        "type": EntityType.LIGHT,
    },
    "STH0A": {
        "type": EntityType.TEMPERATURE,
        "actions": [
            TestAction("thSelfTest"),
            MuteAction(
                "extendMute", "2nd_appmute", extra={"type": "STH0A"}, mute_type="1"
            ),
        ],
    },
    "STH0B": {
        "type": EntityType.TEMPERATURE,
        "actions": [
            TestAction("thSelfTest"),
            MuteAction(
                "extendMute", "2nd_appmute", extra={"type": "STH0B"}, mute_type="1"
            ),
        ],
    },
    "STH0C": {
        "type": EntityType.TEMPERATURE,
        "actions": [WifiExtendedMuteAction()],
    },
    "STH51": {
        "type": EntityType.TEMPERATURE,
        "actions": [
            TestAction("thSelfTest"),
            MuteAction(
                "extendMute", "2nd_appmute", extra={"type": "STH51"}, mute_type="1"
            ),
        ],
    },
    "SWL51": {
        "type": EntityType.LIGHT,
    },
    "SWS0A": {
        "type": EntityType.WATER,
        "actions": [
            TestAction("waterSelfTest", extra={"userParam": "source=1"}),
        ],
    },
    "SWS0B": {
        "type": EntityType.WATER,
        "actions": [WifiWaterMuteAction()],
    },
    "SWS51": {
        "type": EntityType.WATER,
        "actions": [
            TestAction("waterSelfTest"),
            MuteAction(
                shadow="appWater",
                topic="2nd_appwater",
                extra={"silenceTime": "", "setType": "0"},
            ),
        ],
    },
    "CB0Z-3S": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "LP/N-SA-0B": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "LP/N-SCA-0A": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XC0C-iA": {
        "type": EntityType.CO,
        "actions": [WifiAlarmMuteAction()],
    },
    "XC0C-iR": {
        "type": EntityType.CO,
        "actions": [WifiAlarmMuteAction()],
    },
    "XC0M-iR": {
        "type": EntityType.CO,
        "actions": [WifiAlarmMuteAction()],
    },
    "XC01-M": {
        # CO RF
        "type": EntityType.CO,
        "actions": [
            TestAction(shadow="appCoSelfTest"),
            MuteAction("appCoMute", mute_type="1"),
            FireDrillAction(),
        ],
    },
    "XC04-WX": {
        "identifier": lambda entity: f"XC04-WX-{entity.sn}",
        "type": EntityType.CO,
        "actions": [WifiAlarmMuteAction()],
    },
    "XH02-M": {
        "type": EntityType.HEAT,
        "actions": [
            TestAction(shadow="appXh02mSelfTest", extra={"userParam": "source=1"}),
            MuteAction("appXh02mMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XP0A-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("appXp0amrMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XR0A-iR": {
        "type": EntityType.RADON,
        "actions": [WifiExtendedMuteAction()],
    },
    "XP02S-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "XS01-M": {
        "type": EntityType.SMOKE,
        "actions": [
            SmokeRFTestAction(),
            MuteAction(),
            FireDrillAction(),
        ],
    },
    "XS01-WX": {
        "type": EntityType.SMOKE,
        "actions": [
            XS01WXMuteAction(),
        ],
    },
    "XS0B-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XS03-iWX": {
        # Smoke RF
        "type": EntityType.SMOKE,
        "actions": [
            SmokeRFTestAction(),
            SmokeRFAppMuteAction(),
        ],
    },
    "XS03-WX": {
        "type": EntityType.SMOKE,
        "actions": [WifiAlarmMuteAction()],
    },
    "XS0D-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50SmokeMuteAction(),
            FireDrillAction(),
        ],
    },
    "XC0C-MR": {
        "type": EntityType.CO,
        "actions": [
            SBS50SecondGenTestAction(),
            SBS50CoMuteAction(),
            FireDrillAction(),
        ],
    },
    "XP0A-iR": {
        "type": EntityType.COMBI,
        "actions": [WifiAlarmMuteAction()],
    },
    "XP0H-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("appSc07mrMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XP0H-iR": {
        "type": EntityType.COMBI,
        "actions": [WifiAlarmMuteAction()],
    },
    "XP0J-iA": {
        "type": EntityType.COMBI,
        "actions": [
            XP0JTestAction(),
            WifiAlarmMuteAction(),
            FireDrillAction(),
        ],
    },
    "XP0P-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("appSc07mrMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XS0B-iR": {
        "type": EntityType.SMOKE,
        "actions": [WifiAlarmMuteAction()],
    },
    "XS0E-iR": {
        "type": EntityType.SMOKE,
        "actions": [WifiAlarmMuteAction()],
    },
    "XS0F-PMA": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XS0R-iA": {
        "type": EntityType.SMOKE,
        "actions": [
            WifiSelfTestAction(),
            WifiAlarmMuteAction(),
            FireDrillAction(),
        ],
    },
}
