from datetime import datetime, timedelta, timezone

from .entity_map import entities
from .mapping import bool_state, map_values


_ONLINE_TIME_EXCLUDED_TYPES = {
    "SC07-iA",
    "XP0J-iA",
    "XP0S-iA",
    "XP0T-iA",
    "XP0V-iA",
    "XP0W-iA",
    "XS0AA-iA",
    "XS0AB-iA",
    "XS0R-iA",
    "STH0C",
}
_EXTENDED_OFFLINE_HOUR_TYPES = {"SWS0B", "XR0A-iR"}


def _offline_over_hours(entity_type: str | None) -> int:
    return 49 if entity_type in _EXTENDED_OFFLINE_HOUR_TYPES else 34


def _parse_xsense_time(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.strptime(str(value), "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _online_from_report_time(data: dict, entity_type: str | None) -> bool | None:
    if entity_type in _ONLINE_TIME_EXCLUDED_TYPES:
        return None

    online_time = data.get("onlineTime")
    if not online_time:
        return None

    reported = _parse_xsense_time(online_time)
    utc_time = _parse_xsense_time(data.get("utcTime")) or datetime.now(timezone.utc)
    if reported is None:
        return None

    return utc_time <= reported + timedelta(hours=_offline_over_hours(entity_type))


class Entity:
    online = None
    type = None
    _data = None
    entity_type = None

    def __init__(self, **kwargs):
        self.online = None
        self.room_id = kwargs.get("roomId")
        self._data = {}
        self._online_from_explicit_flag = False

        entity = entities.get(self.type, {})
        self.entity_type = entity.get("type")

        for key in ("online", "onLine"):
            if key in kwargs:
                self._set_online(kwargs[key])
                break

    def _set_online(self, value) -> None:
        online = bool_state(value)
        if online is not None:
            self.online = online
            self._online_from_explicit_flag = True

    def set_data(self, values: dict):
        data = values.copy()
        has_online_flag = False
        for key in ("online", "onLine"):
            if key in data:
                self._set_online(data.pop(key))
                has_online_flag = True
                break
        if not has_online_flag:
            online = _online_from_report_time(data, self.type)
            if online is not None:
                # The app treats online/onLine as the authoritative connection
                # state. Report timestamps can confirm a device is awake, but
                # should not turn an explicitly online device offline.
                if (
                    online
                    or self.online is not True
                    or not self._online_from_explicit_flag
                ):
                    self.online = online
                    self._online_from_explicit_flag = False
        status_data = data.get("status")
        if isinstance(status_data, dict):
            data.pop("status", None)
            data.update(status_data)
        if "alarmStatus" not in data and "a" not in data and "isAlarm" in data:
            data["alarmStatus"] = data["isAlarm"]
        peak_data = data.pop("peak", {})
        if isinstance(peak_data, dict):
            if "coPpmPeak" in peak_data:
                data.setdefault("coPpmPeak", peak_data["coPpmPeak"])
            if "radonPeak" in peak_data:
                data.setdefault("radonPeak", peak_data["radonPeak"])
            if "time" in peak_data:
                if "coPpmPeak" in peak_data:
                    data.setdefault("coPpmPeakTime", peak_data["time"])
                if "radonPeak" in peak_data:
                    data.setdefault("radonPeakTime", peak_data["time"])
        for nested_key in ("lightShadowBean", "skp0aShadowBean"):
            nested_data = data.pop(nested_key, {})
            if isinstance(nested_data, dict):
                data.update(nested_data)
        # software versions are reported differently per device
        if "swMain" in data:
            data["network_sw"] = data.get("sw")
            data["sw"] = data.pop("swMain", None)
        self._data.update(map_values(self.type, data))

    @property
    def data(self):
        return self._data

    @property
    def shadow_name(self):
        """Return the AWS IoT thing name used by the X-Sense app."""
        if self.type == "SBS10":
            return self.sn
        if self.type in _SBS50_THING_TYPES:
            return f"SBS50{self._station_sn()}"
        if self.type in _DASHED_THING_TYPES:
            return f"{self.type}-{self.sn}"
        if self.type == "XS01-WX":
            separator = "-" if self._is_xs01wx_v9_serial() else ""
            return f"{self.type}{separator}{self.sn}"
        return f"{self.type}{self.sn}"

    def _is_xs01wx_v9_serial(self) -> bool:
        serial = str(self.sn or "").upper()
        return "EN" in serial or "UL" in serial

    def _station_sn(self) -> str:
        station = getattr(self, "station", None)
        return getattr(station, "sn", None) or self.sn


_DASHED_THING_TYPES = {
    # Mirrors com.claybox.iot.ams.thing.c0.getThingName() plus per-device
    # XsDeviceAlarm.getWiFiThingName() handlers in the Android app.
    "SC06-WX",
    "SC07-WX",
    "SC07-iA",
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XP0S-iA",
    "XP0T-iA",
    "XP0V-iA",
    "XP0W-iA",
    "XR0A-iR",
    "XS0B-iR",
    "XS0AA-iA",
    "XS0AB-iA",
    "XS0R-iA",
}

_SBS50_THING_TYPES = {
    "CB0Z-3S",
    "LP/N-SA-0B",
    "LP/N-SCA-0A",
    "SC01-MN",
    "SD19-MN",
    "SK0Z-3S",
    "STH0B",
    "XC0C-MR",
    "XS0X-MN",
}
