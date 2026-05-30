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
            self.online = data.pop("online") != "0"
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
        return f"{self.type}{self.sn}"
