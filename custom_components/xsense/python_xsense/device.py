from .entity import Entity


class Device(Entity):
    def __init__(self, station, **kwargs):
        self.station = station
        self.entity_id = kwargs.get("deviceId")
        self.type = _first_value(kwargs, ("deviceType", "type", "category"))
        self.name = kwargs.get("deviceName")
        self.sn = _first_value(
            kwargs,
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
        super().__init__(**kwargs)


def _first_value(data: dict, keys: tuple[str, ...]):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None
