from .entity_map import entities
from .mapping import map_values


class Entity:
    online = None
    type = None
    _data = None
    entity_type = None

    def __init__(self, **kwargs):
        self.room_id = kwargs.get("roomId")
        self._data = {}

        entity = entities.get(self.type, {})
        self.entity_type = entity.get("type")

    def set_data(self, values: dict):
        data = values.copy()
        if "online" in data:
            self.online = str(data.pop("online")) != "0"
        if data.get("onlineTime"):
            self.online = True
        status_data = data.pop("status", {}) or {}
        if isinstance(status_data, dict):
            data.update(status_data)
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
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XR0A-iR",
    "XS0B-iR",
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
}
