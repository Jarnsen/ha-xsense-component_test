from typing import List, Dict

from .aws_signer import AWSSigner
from .station import Station
from .mqtt_helper import MQTTHelper
from .entity_map import EntityType


class House:
    rooms: Dict[str, Dict[str, str]] = None
    room_order: List[str] = None

    stations: Dict[str, Station] = None
    station_order: List[str] = None

    def __init__(
        self,
        signer: AWSSigner,
        house_id: str,
        name: str,
        region: str,
        mqtt_region: str,
        mqtt_server: str,
    ):
        self.house_id = house_id
        self.name = name
        self.region = region
        self.mqtt_region = mqtt_region
        self.mqtt_server = mqtt_server
        self.rooms = {}
        self.room_order = []
        self.stations = {}
        self.station_order = []

        self.mqtt = MQTTHelper(signer, self)

    def set_rooms(self, data):
        self.rooms = data.get("houseRooms") or {}
        self.room_order = data.get("roomSort") or []

    def room_name(self, room_id: str | None) -> str | None:
        if not room_id:
            return None
        if isinstance(self.rooms, dict):
            room = self.rooms.get(room_id)
            if isinstance(room, dict):
                return room.get("roomName") or room.get("name")
            if isinstance(room, str):
                return room
        if isinstance(self.rooms, list):
            for room in self.rooms:
                if not isinstance(room, dict):
                    continue
                if room.get("roomId") == room_id:
                    return room.get("roomName") or room.get("name")
        return None

    def set_stations(self, data):
        self.station_order = list(data.get("stationSort") or [])

        stations = {}
        for i in data.get("stations") or []:
            station_id = i.get("stationId")
            if not station_id:
                continue
            s = Station(self, **i)
            s.set_data(
                {
                    key: value
                    for key, value in i.items()
                    if key not in {"devices", "deviceSort", "groupList"}
                }
            )
            s.set_devices(i)

            stations[station_id] = s

        for i in data.get("cameras") or []:
            camera_type = i.get("category")
            station_id = i.get("ipcId")
            if not station_id:
                continue
            if station_id in stations:
                continue

            station_data = {
                "stationId": station_id,
                "roomId": i.get("roomId"),
                "stationSn": i.get("ipcSn"),
                "stationName": i.get("ipcName"),
                "category": camera_type,
                "deviceType": camera_type,
                "userId": i.get("userId"),
                "userName": i.get("userName"),
                "onLine": 1,
                "devices": [],
            }
            s = Station(self, **station_data)
            s.set_data(
                {
                    key: value
                    for key, value in station_data.items()
                    if key not in {"devices", "deviceSort", "groupList"}
                }
            )
            s.entity_type = EntityType.CAMERA
            s.set_devices(station_data)
            stations[station_id] = s

        self.stations = stations

    def get_station_by_sn(self, sn: str):
        return next((i for _, i in self.stations.items() if i.sn == sn), None)
