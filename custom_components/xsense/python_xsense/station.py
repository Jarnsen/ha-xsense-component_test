from typing import List, Dict

from .device import Device
from .entity import Entity


class Station(Entity):
    devices: Dict[str, Device]
    device_order: List[str]
    device_by_sn: Dict[str, str]

    def __init__(self, parent, **kwargs):
        self.house = parent
        self.safe_mode = kwargs.get("safeMode")
        self.entity_id = kwargs.get("stationId")
        self.name = kwargs.get("stationName")
        self.sn = _first_value(
            kwargs,
            (
                "stationSn",
                "stationSN",
                "_stationSN",
                "_stationSn",
                "stationSerialNumber",
                "serialNumber",
                "sn",
            ),
        )
        self.online = None
        self.type = _first_value(kwargs, ("category", "deviceType", "type"))

        self.devices = {}
        self.device_order = []
        self.device_by_sn = {}
        self.has_alarm = False
        self._alarm_data = {}
        super().__init__(**kwargs)

    def set_devices(self, data):
        self.device_order = data.get("deviceSort") or []
        result = {}
        result_sn = {}
        source_devices = []
        for i in data.get("devices") or []:
            device_data = dict(i)
            device_id = _first_value(device_data, "deviceId", "id")
            device_sn = _first_value(
                device_data,
                "deviceSn",
                "deviceSN",
                "_deviceSN",
                "_deviceSn",
                "devSerialNumber",
                "serialNumber",
                "sn",
            )
            if device_sn in (None, ""):
                continue
            if device_id in (None, ""):
                device_id = device_sn
            device_data["deviceId"] = device_id
            device_data["deviceSn"] = device_sn
            device_data["stationId"] = self.entity_id
            device_sn = _device_serial(device_data)
            device_id = _first_value(device_data, ("deviceId",)) or device_sn
            if device_id in (None, "") or device_sn in (None, ""):
                continue
            device_data["deviceId"] = str(device_id)
            device_data["deviceSn"] = str(device_sn)
            if not device_data.get("roomName") and self.house is not None:
                device_data["roomName"] = self.house.room_name(device_data.get("roomId"))
            if "isActivate" in device_data:
                device_data["activate"] = device_data["isActivate"]
            source_devices.append(device_data)
            d = Device(self, **device_data)
            data_updates = {}
            if device_data.get("roomName") is not None:
                data_updates["roomName"] = device_data["roomName"]
            if device_data.get("stationId") is not None:
                data_updates["stationId"] = device_data["stationId"]
            if "isActivate" in device_data:
                data_updates.update(
                    {
                        "activate": device_data["isActivate"],
                        "isActivate": device_data["isActivate"],
                    }
                )
            if data_updates:
                d.set_data(data_updates)
            result[device_data["deviceId"]] = d
            result_sn[str(device_data["deviceSn"])] = device_data["deviceId"]

        for i in data.get("groupList") or []:
            device_data = _light_group_device_data(self, data, i, source_devices)
            d = Device(self, **device_data)
            d.set_data(device_data)
            result[device_data["deviceId"]] = d
            result_sn[str(device_data["deviceSn"])] = device_data["deviceId"]
        self.devices = result
        self.device_by_sn = result_sn

    def get_device_by_sn(self, sn: str):
        if device_id := self.device_by_sn.get(str(sn)):
            return self.devices.get(device_id)
        return None

    def get_device_by_identifier(self, identifier: str):
        """Return a child device by app id or serial identifier."""
        identifier = str(identifier)
        return self.devices.get(identifier) or self.get_device_by_sn(identifier)

    def get_group_device(self, group_id):
        group_id = _java_string(group_id)
        for dev in self.devices.values():
            if (
                dev.type == "group-L"
                and _java_string(dev.data.get("groupId")) == group_id
            ):
                return dev
        return None

    def set_alarm_data(self, values: dict):
        keys = [
            "mode",
            "who",
            "safeMode",
            "entryDelay",
            "pword",
            "deviceSn",
            "forceArm",
            "forceReason",
        ]

        for k in keys:
            if k in values:
                self._alarm_data[k] = values[k]

    @property
    def alarm_data(self):
        return self._alarm_data

    @property
    def alarm_mode(self):
        """Return the current security mode reported by X-Sense."""
        return (
            self._alarm_data.get("mode")
            or self._alarm_data.get("safeMode")
            or self.safe_mode
            or self.data.get("safeMode")
        )

    @property
    def is_armed(self) -> bool | None:
        """Return whether the security mode is armed when it is known."""
        mode = self.alarm_mode
        if mode in (None, ""):
            return None
        normalized = str(mode).strip().lower()
        if normalized in {"0", "disarm", "disarmed", "off"}:
            return False
        if normalized in {"1", "2", "home", "away", "armed", "armed_home", "armed_away"}:
            return True
        return None


def _light_group_device_data(
    station: Station, station_data: Dict, group: Dict, source_devices: List[Dict]
) -> Dict:
    group_id = group.get("groupId")
    group_name = group.get("groupName")
    create_time = group.get("createTime") or ""
    members = [i for i in source_devices if i.get("groupId") == group_id]
    return {
        "deviceName": group_name,
        "deviceId": f"{create_time}{_java_string(group_id)}",
        "deviceSn": _light_group_device_sn(group_id),
        "groupId": group_id,
        "groupName": group_name,
        "stationId": station.entity_id,
        "stationSn": station.sn,
        "houseId": station.house.house_id if station.house is not None else None,
        "deviceType": "group-L",
        "appTime": group.get("appTime"),
        "pirTime": group.get("pirTime"),
        "roomId": station_data.get("roomId"),
        "roomName": station_data.get("roomName")
        or (station.house.room_name(station.room_id) if station.house is not None else None),
        "devs": [i.get("deviceSn") for i in members if i.get("deviceSn")],
        "on": "1" if _has_light_on(members) else "0",
    }


def _device_serial(data: Dict):
    return _first_value(
        data,
        (
            "deviceSn",
            "deviceSN",
            "_deviceSN",
            "_deviceSn",
            "devSerialNumber",
            "serialNumber",
            "sn",
        ),
    )


def _has_light_on(devices: List[Dict]) -> bool:
    return any(_is_not_reported_offline(i) and i.get("on") == "1" for i in devices)


def _is_not_reported_offline(device: Dict) -> bool:
    online = device.get("online", device.get("onLine"))
    return online not in (0, "0", False, "false", "False")


def _light_group_device_sn(group_id) -> str:
    if group_id is None:
        return "LG000000"
    padded = _java_string(group_id).rjust(8, "0")
    return f"LG{padded[2:]}"


def _java_string(value) -> str:
    return "null" if value is None else str(value)


def _first_value(data: Dict, *keys):
    if len(keys) == 1 and isinstance(keys[0], (tuple, list)):
        keys = tuple(keys[0])
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None
