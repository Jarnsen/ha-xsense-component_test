from .entity import Entity


class Device(Entity):
    def __init__(self, station, **kwargs):
        self.station = station
        self.entity_id = _first_value(kwargs, "deviceId", "id")
        self.type = _first_value(kwargs, "deviceType", "type", "category")
        self.name = _first_value(kwargs, "deviceName", "name")
        self.sn = _first_value(
            kwargs,
            "deviceSn",
            "deviceSN",
            "_deviceSN",
            "_deviceSn",
            "devSerialNumber",
            "serialNumber",
            "sn",
        )
        super().__init__(**kwargs)


def _first_value(data: dict, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None
