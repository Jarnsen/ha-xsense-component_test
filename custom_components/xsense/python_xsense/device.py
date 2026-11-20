from .entity import Entity, _parse_xsense_time
from .mapping import bool_state

LOCAL_MQTT_ALARM_MODELS = frozenset({"XS0B-MR", "XS01-M", "XH02-M"})


class Device(Entity):
    def __init__(self, station, **kwargs):
        self.station = station
        self.entity_id = kwargs.get("deviceId")
        self.type = _first_value(kwargs, ("deviceType", "type", "category"))
        self.name = kwargs.get("deviceName")
        self.cloud_alarm_clear_time = None
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

    def set_data(self, values: dict):
        super().set_data(values)
        if self.type not in LOCAL_MQTT_ALARM_MODELS or getattr(self.station, "type", None) != "SBS50":
            return
        status = values.get("status")
        if not isinstance(status, dict):
            status = values
        alarm = _first_value(status, ("alarmStatus", "a"))
        if alarm is not None:
            self.cloud_alarm_clear_time = (
                _parse_xsense_time(status.get("time")) if bool_state(alarm) is False else None
            )


def _first_value(data: dict, keys: tuple[str, ...]):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None
