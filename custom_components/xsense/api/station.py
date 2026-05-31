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
        self.sn = kwargs.get("stationSn")
        self.online = kwargs.get("onLine", True)
        self.type = kwargs.get("category")

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
        for i in data.get("devices") or []:
            d = Device(self, **i)
            result[i["deviceId"]] = d
            result_sn[i["deviceSn"]] = i["deviceId"]
        self.devices = result
        self.device_by_sn = result_sn

    def get_device_by_sn(self, sn: str):
        if device_id := self.device_by_sn.get(sn):
            return self.devices.get(device_id)
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
            if v := values.get(k):
                self._alarm_data[k] = v

    @property
    def alarm_data(self):
        return self._alarm_data
