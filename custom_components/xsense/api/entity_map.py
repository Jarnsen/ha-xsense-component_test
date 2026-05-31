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


def _smoke_rf_test_shadow(entity) -> str:
    return "app2ndSelfTest" if _is_smoke_v9(entity) else "appSelfTest"


def _smoke_rf_test_extra(entity) -> Dict:
    return {"userParam": "source=1"} if _is_smoke_v9(entity) else {}


def SmokeRFTestAction():
    return TestAction(_smoke_rf_test_shadow, extra=_smoke_rf_test_extra)


def WifiSelfTestAction():
    return TestAction(
        "appSelfTest", extra={"userParam": "source=1"}, target=lambda entity: entity
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


def XS01WXTestAction():
    """XS01-WX self test for standalone and SBS50-linked Wi-Fi smoke devices."""
    return {
        "action": "test",
        "topic": lambda entity: (
            f"2nd_selftest_{entity.sn}"
            if getattr(getattr(entity, "station", None), "type", None) == "SBS50"
            else f"appselftest_{entity.sn}"
        ),
        "shadow": "appSelfTest",
        "time_format": lambda entity: (
            "epoch_ms"
            if getattr(getattr(entity, "station", None), "type", None) == "SBS50"
            else None
        ),
    }


def _is_smoke_v9(entity) -> bool:
    try:
        return int(entity.data.get("smokeEdition", 0)) >= 9
    except (TypeError, ValueError):
        return False


def XS01WXMuteAction():
    return MuteAction(
        topic=lambda entity: "2nd_appmute" if _is_smoke_v9(entity) else "appmute",
        mute_type="0",
    )


def SC07MRMuteAction():
    return MuteAction(
        shadow=lambda entity: "app2ndMute" if _is_smoke_v9(entity) else "appSc07mrMute",
        mute_type="1",
        extra={"userParam": "source=1"},
    )


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
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "SC06-WX": {
        "identifier": lambda entity: f"SC06-WX-{entity.sn}",
        "type": EntityType.COMBI,
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
        "actions": [MuteAction(mute_type="1")],
    },
    "SD11-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            FireDrillAction(),
        ],
    },
    "SD19-MN": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
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
            {
                "action": "mute",
                "topic": lambda x: "2nd_appmailmute",
                "shadow": "appMailMute",
                "data": {"silenceTime": "", "setType": ""},
            },
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
    },
    "XC0C-iR": {
        "type": EntityType.CO,
    },
    "XC0M-iR": {
        "type": EntityType.CO,
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
        "actions": [MuteAction(mute_type="1")],
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
    },
    "XP02S-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
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
            XS01WXTestAction(),
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
        ],
    },
    "XS03-WX": {
        "type": EntityType.SMOKE,
    },
    "XS0D-MR": {
        "type": EntityType.SMOKE,
        "actions": [
            SBS50SecondGenTestAction(),
            FireDrillAction(),
        ],
    },
    "XC0C-MR": {
        "type": EntityType.CO,
        "actions": [
            SBS50SecondGenTestAction(),
            FireDrillAction(),
        ],
    },
    "XP0A-iR": {
        "type": EntityType.COMBI,
    },
    "XP0H-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XP0H-iR": {
        "type": EntityType.COMBI,
    },
    "XP0J-iA": {
        "type": EntityType.COMBI,
        "actions": [
            WifiSelfTestAction(),
            FireDrillAction(),
        ],
    },
    "XP0P-MR": {
        "type": EntityType.COMBI,
        "actions": [
            SBS50SecondGenTestAction(),
            MuteAction("app2ndMute", mute_type="1", extra={"userParam": "source=1"}),
            FireDrillAction(),
        ],
    },
    "XS0B-iR": {
        "type": EntityType.SMOKE,
    },
    "XS0E-iR": {
        "type": EntityType.SMOKE,
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
            FireDrillAction(),
        ],
    },
}
